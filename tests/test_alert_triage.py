from __future__ import annotations

import json
from pathlib import Path

import pytest

from patchwise.core.alert_triage import (
    canonical, export_jira_draft, get_investigation, group_id_for, import_events,
    investigation_snapshot, list_alert_groups, normalize_event, parse_events, save_investigation,
)
from patchwise.core.database import get_session_factory
from patchwise.core.models import AlertEvent

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def rows():
    return json.loads((EXAMPLES / "identity-network-events.json").read_text())


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "triage.db")


def reviewed_values(event_id):
    return {"summary": f"Investigate the sign-in ({event_id}); compromise is unconfirmed.",
            "timeline_notes": f"09:01 UTC: observed {event_id}", "supporting_evidence": f"MFA absent ({event_id})",
            "evidence_ids": [event_id], "missing_context": "Confirm VPN and user activity",
            "disposition": "Suspicious", "escalation_rationale": "Request context before escalation", "reviewed": True}


def test_duplicate_grouping_is_deterministic_and_retains_ids(rows, db, tmp_path):
    result = import_events(rows, db)
    assert result == {"added": 6, "already_present": 0, "groups": 4}
    groups = list_alert_groups(db)
    duplicate = next(group for group in groups if group["events"][0]["event_id"] == "signin-001")
    assert {event["event_id"] for event in duplicate["events"]} == {"signin-001", "signin-001-copy"}
    assert "signin-benign-002" not in {event["event_id"] for event in duplicate["events"]}
    other_db = str(tmp_path / "reversed.db")
    import_events(list(reversed(rows)), other_db)
    assert {group["group_id"] for group in groups} == {group["group_id"] for group in list_alert_groups(other_db)}
    assert import_events(rows, db)["already_present"] == 6
    with get_session_factory(db)() as session:
        stored = session.get(AlertEvent, "signin-001")
        assert json.loads(stored.raw_json) == rows[0]


def test_bucket_evidence_and_timezone_boundaries(rows):
    original = normalize_event(rows[0])
    assert group_id_for(original) == group_id_for(normalize_event({**rows[0], "timestamp": "2026-10-01T05:01:00-04:00"}))
    assert group_id_for(original) != group_id_for(normalize_event({**rows[0], "timestamp": "2026-10-01T09:05:00Z"}))
    assert group_id_for(original) != group_id_for(normalize_event({**rows[0], "evidence": {**rows[0]["evidence"], "mfa": True}}))
    reordered = dict(reversed(list(rows[0]["evidence"].items())))
    assert group_id_for(original) == group_id_for(normalize_event({**rows[0], "evidence": reordered}))


def test_incomplete_events_remain_traceable_without_fabricated_time(db):
    rows = [{"event_id": "gap-1"}, {"event_id": "gap-2", "timestamp": "2026-10-01T09:00:00"}]
    assert import_events(rows, db)["groups"] == 2
    for group in list_alert_groups(db):
        event = group["events"][0]
        assert event["timestamp"] is None
        assert "evidence" in event["missing_context"]
        assert "user or host" in event["missing_context"]
    idless = normalize_event({"source": "test"})
    assert idless["event_id"] == normalize_event({"source": "test"})["event_id"]
    assert idless["event_id"].startswith("generated-")


def test_json_csv_equivalence_and_invalid_imports(rows):
    parsed_json = parse_events((EXAMPLES / "identity-network-events.json").read_bytes(), ".json")
    parsed_csv = parse_events((EXAMPLES / "identity-network-events.csv").read_bytes(), ".csv")
    assert [normalize_event(row) for row in parsed_csv] == [normalize_event(row) for row in parsed_json]
    for data in (b"not json", b"{}", b"[]", b"[1]", b'[{"evidence": []}]'):
        with pytest.raises(ValueError):
            parse_events(data, "json")
    with pytest.raises(ValueError, match="2 MiB"):
        parse_events(b" " * (2 * 1024 * 1024 + 1), "json")


def test_collision_rolls_back_batch(rows, db):
    import_events([rows[0]], db)
    with pytest.raises(ValueError, match="collision"):
        import_events([rows[2], {**rows[0], "severity": "low"}], db)
    assert sum(len(group["events"]) for group in list_alert_groups(db)) == 1


def test_manual_review_export_without_key(rows, db, monkeypatch):
    monkeypatch.delenv("PATCHWISE_AI_API_KEY", raising=False)
    import_events(rows[:2], db)
    group_id = group_id_for(normalize_event(rows[0]))
    with pytest.raises(ValueError, match="analyst-reviewed"):
        export_jira_draft(group_id, db)
    values = reviewed_values("signin-001")
    save_investigation(group_id, values, db)
    draft = export_jira_draft(group_id, db)
    for text in ("signin-001", "signin-001-copy", "2026-10-01T09:01:00Z", "Escalation rationale", "MFA absent", "src_ip", "No ticket has been created"):
        assert text in draft
    assert investigation_snapshot(group_id, db)["investigation"]["reviewed"]
    assert get_investigation(group_id, db)["summary"] == values["summary"]
    with pytest.raises(ValueError, match="belong"):
        save_investigation(group_id, {**values, "evidence_ids": ["bogus"]}, db)
    assert get_investigation(group_id, db)["reviewed"]  # Failed save does not replace valid record.


def test_new_duplicate_requires_fresh_review(rows, db):
    import_events(rows[:1], db)
    group_id = group_id_for(normalize_event(rows[0]))
    save_investigation(group_id, reviewed_values("signin-001"), db)
    import_events(rows[:1], db)
    assert get_investigation(group_id, db)["reviewed"]
    import_events(rows[1:2], db)
    assert not get_investigation(group_id, db)["reviewed"]
    with pytest.raises(ValueError):
        export_jira_draft(group_id, db)
