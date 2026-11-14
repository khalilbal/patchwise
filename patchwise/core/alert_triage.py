"""Local event intake, exact-evidence-v1 grouping, analyst records and exports.

No scanner findings are modified. See docs/alert-triage.md for the grouping contract.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from patchwise.core.database import get_session_factory, init_db
from patchwise.core.models import AlertEvent, AlertGroup, AlertInvestigation

RULE_VERSION = "exact-evidence-v1"
DISPOSITIONS = ["Investigating", "Suspicious", "Benign", "Inconclusive", "Escalation proposed"]
MAX_BYTES = 2 * 1024 * 1024
MAX_EVENTS = 5000


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _scalar(row: dict, field: str, default: str = "") -> str:
    value = row.get(field)
    if value is None:
        return default
    if not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"{field} must be a scalar value")
    result = str(value).strip()
    if len(result) > 255:
        raise ValueError(f"{field} exceeds 255 characters")
    return result or default


def normalize_event(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Each event must be an object")
    missing = []
    timestamp = None
    raw_time = _scalar(row, "timestamp")
    if raw_time:
        try:
            parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise ValueError("Timezone required")
            timestamp = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (ValueError, OverflowError):
            missing.append("timestamp (missing, invalid, or timezone absent)")
    else:
        missing.append("timestamp (missing, invalid, or timezone absent)")

    evidence = row.get("evidence")
    if isinstance(evidence, str):
        if evidence.strip():
            try:
                evidence = json.loads(evidence)
            except json.JSONDecodeError:
                evidence = {"message": evidence}
        else:
            evidence = {}
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object or a JSON object in CSV")
    # Validates JSON serializability, including rejecting NaN and Infinity.
    canonical(evidence)
    if not evidence or all(value in (None, "", [], {}) for value in evidence.values()):
        missing.append("evidence")
    event = {
        "timestamp": timestamp,
        "source": _scalar(row, "source", "unknown").lower(),
        "event_type": _scalar(row, "event_type", "unknown").lower(),
        "severity": _scalar(row, "severity", "unknown").lower(),
        "user": _scalar(row, "user"),
        "host": _scalar(row, "host"),
        "evidence": evidence,
    }
    for field in ("source", "event_type", "severity"):
        if event[field] == "unknown":
            missing.append(field)
    if event["severity"] not in {"critical", "high", "medium", "low", "info", "unknown"}:
        event["severity"] = "unknown"
        missing.append("severity (unrecognized)")
    if not event["user"] and not event["host"]:
        missing.append("user or host")
    event["event_id"] = _scalar(row, "event_id") or f"generated-{digest(event)}"
    event["missing_context"] = missing
    return event


def group_id_for(event: dict) -> str:
    """Five-minute UTC bucket plus exact normalized identity and evidence.

    Incomplete events get their own group; reimporting an ID is still idempotent.
    """
    if event["missing_context"]:
        return digest([RULE_VERSION, "incomplete", event["event_id"]])
    timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
    bucket = int(timestamp.timestamp()) // 300
    return digest([RULE_VERSION, bucket, *[event[key] for key in
        ("source", "event_type", "severity", "user", "host", "evidence")]])


def parse_events(data: bytes | str, file_type: str) -> list[dict]:
    if isinstance(data, str):
        data = data.encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("Import exceeds the 2 MiB limit")
    try:
        content = data.decode("utf-8-sig")
        if file_type.lower().lstrip(".") == "json":
            rows = json.loads(content)
            if not isinstance(rows, list):
                raise ValueError("JSON must contain an array of events")
        elif file_type.lower().lstrip(".") == "csv":
            rows = list(csv.DictReader(io.StringIO(content)))
        else:
            raise ValueError("Use JSON or CSV")
        if not rows or len(rows) > MAX_EVENTS:
            raise ValueError("Import must contain 1 to 5000 events")
        for index, row in enumerate(rows, 1):
            try:
                normalize_event(row)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid event at row {index}: {exc}") from None
        return rows
    except (UnicodeError, json.JSONDecodeError, csv.Error, RecursionError):
        raise ValueError("Could not parse the UTF-8 JSON/CSV import") from None


def import_events(rows: list[dict], db_path: str | None = None) -> dict:
    if not rows or len(rows) > MAX_EVENTS:
        raise ValueError("Import must contain 1 to 5000 events")
    # Validate the entire batch before beginning a transaction.
    normalized = [(row, normalize_event(row)) for row in rows]
    init_db(db_path)
    added = repeated = 0
    groups = set()
    with get_session_factory(db_path)() as session:
        for raw, event in normalized:
            event_id = event["event_id"]
            existing = session.get(AlertEvent, event_id)
            if existing:
                if existing.normalized_json != canonical(event):
                    raise ValueError(f"Event ID collision: {event_id}. Import rolled back; IDs must be globally unique.")
                repeated += 1
                groups.add(existing.group_id)
                continue
            group_id = group_id_for(event)
            if session.get(AlertGroup, group_id) is None:
                session.add(AlertGroup(id=group_id, rule_version=RULE_VERSION))
                session.flush()
            session.add(AlertEvent(event_id=event_id, group_id=group_id,
                                   normalized_json=canonical(event), raw_json=canonical(raw)))
            # Explicit flush: session autoflush is disabled in the existing database helper.
            session.flush()
            investigation = session.get(AlertInvestigation, group_id)
            if investigation:
                investigation.reviewed = False  # New evidence requires another review.
            added += 1
            groups.add(group_id)
        session.commit()
    return {"added": added, "already_present": repeated, "groups": len(groups)}


def list_alert_groups(db_path: str | None = None) -> list[dict]:
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        records = session.scalars(select(AlertEvent).order_by(AlertEvent.event_id)).all()
        investigations = {item.group_id: item for item in session.scalars(select(AlertInvestigation)).all()}
        grouped = {}
        for record in records:
            event = json.loads(record.normalized_json)
            group = grouped.setdefault(record.group_id, {
                "group_id": record.group_id, "events": [], "disposition": "Unreviewed", "reviewed": False,
            })
            group["events"].append(event)
        for group in grouped.values():
            group["events"].sort(key=lambda event: (event["timestamp"] or "~", event["event_id"]))
            investigation = investigations.get(group["group_id"])
            if investigation:
                group.update(disposition=investigation.disposition, reviewed=investigation.reviewed)
        return list(grouped.values())


def get_group_events(group_id: str, db_path: str | None = None) -> list[dict]:
    for group in list_alert_groups(db_path):
        if group["group_id"] == group_id:
            return group["events"]
    raise ValueError("Alert group does not exist")


def get_investigation(group_id: str, db_path: str | None = None) -> dict:
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        record = session.get(AlertInvestigation, group_id)
        if record is None:
            return {"group_id": group_id, "summary": "", "timeline_notes": "", "supporting_evidence": "",
                    "evidence_ids": [], "missing_context": "", "disposition": "Investigating",
                    "escalation_rationale": "", "reviewed": False, "updated_at": None}
        result = {column.name: getattr(record, column.name) for column in record.__table__.columns}
        result["evidence_ids"] = json.loads(result.pop("evidence_ids_json"))
        result["updated_at"] = record.updated_at.isoformat() + "Z"
        return result


def save_investigation(group_id: str, values: dict, db_path: str | None = None) -> None:
    events = get_group_events(group_id, db_path)
    allowed = {event["event_id"] for event in events}
    ids = values.get("evidence_ids", [])
    if not isinstance(ids, list) or any(not isinstance(item, str) or item not in allowed for item in ids):
        raise ValueError("Supporting evidence IDs must belong to this group")
    if values.get("disposition") not in DISPOSITIONS:
        raise ValueError("Choose a valid disposition")
    if values.get("reviewed") and any(not str(values.get(field, "")).strip() for field in
                                      ("summary", "supporting_evidence", "missing_context", "escalation_rationale")):
        raise ValueError("Review requires a summary, supporting evidence, missing context (or 'None identified'), and escalation rationale")
    if values.get("reviewed") and not ids:
        raise ValueError("Review requires at least one supporting event ID")
    with get_session_factory(db_path)() as session:
        record = session.get(AlertInvestigation, group_id)
        if record is None:
            record = AlertInvestigation(group_id=group_id)
            session.add(record)
        for field in ("summary", "timeline_notes", "supporting_evidence", "missing_context", "disposition", "escalation_rationale"):
            setattr(record, field, str(values.get(field, "")))
        record.evidence_ids_json = canonical(sorted(set(ids)))
        record.reviewed = bool(values.get("reviewed", False))
        record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.commit()


def investigation_snapshot(group_id: str, db_path: str | None = None) -> dict:
    return {"rule_version": RULE_VERSION, "investigation": get_investigation(group_id, db_path),
            "events": get_group_events(group_id, db_path)}


def export_jira_draft(group_id: str, db_path: str | None = None) -> str:
    snapshot = investigation_snapshot(group_id, db_path)
    record, events = snapshot["investigation"], snapshot["events"]
    if not record["reviewed"]:
        raise ValueError("Save an analyst-reviewed investigation before exporting a ticket draft")
    lines = ["# Jira ticket draft — analyst reviewed", "", "No ticket has been created or escalated.", "",
             f"Group: {group_id}", f"Disposition: {record['disposition']}",
             f"Reviewed at (UTC): {record['updated_at']}", "", "## Summary", record["summary"],
             "", "## Timeline (UTC)"]
    for event in events:
        lines.append(f"- {event['timestamp'] or 'UNKNOWN TIME'} | {event['event_id']} | "
                     f"{event['source']} | {event['event_type']} | user={event['user'] or 'unknown'} | "
                     f"host={event['host'] or 'unknown'}")
    lines += [record["timeline_notes"], "", "## Supporting evidence", record["supporting_evidence"],
              "Cited event IDs: " + ", ".join(record["evidence_ids"]), "", "## Available event evidence"]
    for event in events:
        lines += [f"Event ID: {event['event_id']}", canonical(event["evidence"]),
                  "Intake gaps: " + (", ".join(event["missing_context"]) or "None identified")]
    lines += ["", "## Missing context", record["missing_context"], "", "## Escalation rationale",
              record["escalation_rationale"], "", "## Underlying event IDs", *[event["event_id"] for event in events]]
    return "\n".join(lines) + "\n"
