"""Run a local DuckDB synthetic log investigation and export directly to Patchwise.

Run from the repo root: python -m labs.signin.run_query --output exports/signin-run-01
Does not import into the app, call AI, or make an analyst decision.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "examples/identity-network-events.json"
QUERY = Path(__file__).with_name("investigate.sql")
FIELDS = ["event_id", "timestamp", "source", "event_type", "severity", "user", "host", "evidence"]


def run_query(output: Path, purpose: str = "user-run") -> dict:
    import duckdb  # Optional: pip install -r requirements-lab.txt

    if purpose not in {"user-run", "automated-check"}:
        raise ValueError("Invalid execution purpose")
    source_bytes, query_bytes = SOURCE.read_bytes(), QUERY.read_bytes()
    source = json.loads(source_bytes)
    with duckdb.connect(":memory:") as connection:
        connection.execute('CREATE TABLE events (event_id VARCHAR, timestamp VARCHAR, source VARCHAR, '
                           'event_type VARCHAR, severity VARCHAR, "user" VARCHAR, host VARCHAR, evidence VARCHAR)')
        connection.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
            [json.dumps(row[field], sort_keys=True) if field == "evidence" else row[field] for field in FIELDS]
            for row in source
        ])
        result = connection.execute(query_bytes.decode())
        if [column[0] for column in result.description] != FIELDS:
            raise ValueError("Query must return the eight Patchwise columns in their original order")
        rows = [dict(zip(FIELDS, values)) for values in result.fetchall()]
    for row in rows:
        row["evidence"] = json.loads(row["evidence"])
    from patchwise.core.alert_triage import parse_events
    events_json = json.dumps(rows, indent=2) + "\n"
    parse_events(events_json, "json")
    # Never overwrite an earlier run or a user's evidence.
    output.mkdir(parents=True, exist_ok=False)
    (output / "events.json").write_text(events_json)
    with (output / "events.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows([{**row, "evidence": json.dumps(row["evidence"], sort_keys=True)} for row in rows])
    (output / "query.sql").write_bytes(query_bytes)
    manifest = {"data_label": "SYNTHETIC", "tool": "DuckDB", "tool_version": duckdb.__version__,
                "purpose": purpose, "executed_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": "examples/identity-network-events.json", "row_count": len(rows),
                "event_ids": [row["event_id"] for row in rows],
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "query_sha256": hashlib.sha256(query_bytes).hexdigest(),
                "export_sha256": hashlib.sha256(events_json.encode()).hexdigest()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="A NEW evidence directory")
    parser.add_argument("--purpose", choices=["user-run", "automated-check"], default="user-run")
    args = parser.parse_args()
    print(json.dumps(run_query(args.output, args.purpose), indent=2))


if __name__ == "__main__":
    main()
