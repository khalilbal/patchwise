"""Paired triage benchmark storage and reproducible CSV analysis (no fabricated results)."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path
from statistics import median

from sqlalchemy import select

from patchwise.core.alert_triage import digest
from patchwise.core.database import get_session_factory, init_db
from patchwise.core.models import TriageBenchmarkRun

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
FIELDS = ["participant", "case_id", "workflow", "case_set_sha256", "elapsed_seconds", "evidence_missed",
          "unsupported_claims", "ai_mistake", "analyst_correction"]


def benchmark_cases() -> tuple[list[dict], str]:
    cases = json.loads((EXAMPLES / "benchmark-cases.json").read_text())
    events = json.loads((EXAMPLES / "identity-network-events.json").read_text())
    return cases, digest({"cases": cases, "events": events})


def validate_run(row: dict) -> dict:
    cases, fingerprint = benchmark_cases()
    result = {field: row.get(field, "") for field in FIELDS}
    if result["case_id"] not in {case["case_id"] for case in cases}:
        raise ValueError("Unknown benchmark case")
    if result["workflow"] not in {"manual", "ai-assisted"}:
        raise ValueError("Workflow must be manual or ai-assisted")
    if not isinstance(result["participant"], str) or not result["participant"].strip():
        raise ValueError("Enter a participant pseudonym")
    if result["case_set_sha256"] != fingerprint:
        raise ValueError("Case dataset fingerprint does not match the bundled benchmark")
    try:
        elapsed = float(result["elapsed_seconds"])
    except (ValueError, TypeError):
        raise ValueError("Elapsed time must be a positive number") from None
    if not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError("Elapsed time must be a positive finite number")
    result["elapsed_seconds"] = elapsed
    for field in ("evidence_missed", "unsupported_claims"):
        value = str(result[field])
        if not value.isdigit():
            raise ValueError(f"{field} must be a nonnegative integer")
        result[field] = int(value)
    if result["evidence_missed"] > len(next(case for case in cases if case["case_id"] == result["case_id"])["required_evidence"]):
        raise ValueError("Evidence missed exceeds this case's rubric items")
    if result["ai_mistake"] and not result["analyst_correction"]:
        raise ValueError("Record the analyst correction for the AI mistake")
    return result


def save_run(row: dict, db_path: str | None = None) -> None:
    row = validate_run(row)
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        existing = session.scalar(select(TriageBenchmarkRun).where(
            TriageBenchmarkRun.participant == row["participant"],
            TriageBenchmarkRun.case_id == row["case_id"],
            TriageBenchmarkRun.workflow == row["workflow"],
            TriageBenchmarkRun.case_set_sha256 == row["case_set_sha256"]))
        if existing:
            raise ValueError("This participant/case/workflow is already recorded; use a new participant/session pseudonym for another trial")
        session.add(TriageBenchmarkRun(**row))
        session.commit()


def list_runs(db_path: str | None = None) -> list[dict]:
    init_db(db_path)
    with get_session_factory(db_path)() as session:
        return [{**{field: getattr(record, field) for field in FIELDS},
                 "recorded_at_utc": record.created_at.isoformat() + "Z"}
                for record in session.scalars(select(TriageBenchmarkRun).order_by(TriageBenchmarkRun.id)).all()]


def export_csv(rows: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        # Spreadsheet formula injection protection for analyst-entered text.
        writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value)
                         for key, value in row.items() if key in FIELDS})
    return output.getvalue()


def summarize(rows: list[dict]) -> dict:
    pairs = {}
    for raw in rows:
        row = validate_run(raw)
        key = (row["participant"], row["case_id"], row["case_set_sha256"])
        pair = pairs.setdefault(key, {})
        if row["workflow"] in pair:
            raise ValueError("Duplicate participant/case/workflow rows; isolate a single trial")
        pair[row["workflow"]] = row
    complete = [pair for pair in pairs.values() if set(pair) == {"manual", "ai-assisted"}]
    result = {"paired_cases": len(complete), "unpaired_cases_excluded": len(pairs) - len(complete)}
    if not complete:
        return result
    manual = median(pair["manual"]["elapsed_seconds"] for pair in complete)
    assisted = median(pair["ai-assisted"]["elapsed_seconds"] for pair in complete)
    result.update(manual_median_seconds=manual, ai_assisted_median_seconds=assisted,
                  change_seconds=assisted - manual, change_percent=100 * (assisted - manual) / manual,
                  median_paired_change_seconds=median(pair["ai-assisted"]["elapsed_seconds"] - pair["manual"]["elapsed_seconds"] for pair in complete))
    for workflow in ("manual", "ai-assisted"):
        result[workflow + "_evidence_missed"] = sum(pair[workflow]["evidence_missed"] for pair in complete)
        result[workflow + "_unsupported_claims"] = sum(pair[workflow]["unsupported_claims"] for pair in complete)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, required=True, help="Exported benchmark CSV")
    args = parser.parse_args()
    with args.csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
