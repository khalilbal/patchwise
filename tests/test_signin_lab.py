"""Automated synthetic smoke checks, not analyst investigation/benchmark results."""
import hashlib
import json

import pytest

pytest.importorskip("duckdb", reason="Optional: pip install -r requirements-lab.txt")

from labs.signin.run_query import SOURCE, run_query
from patchwise.core.alert_triage import import_events, list_alert_groups, normalize_event, parse_events


def test_query_preserves_exact_source_events_and_imports_idempotently(tmp_path):
    output = tmp_path / "query-run"
    manifest = run_query(output, purpose="automated-check")
    exported = parse_events((output / "events.json").read_bytes(), "json")
    expected = [row for row in json.loads(SOURCE.read_text()) if row["user"] == "alex@example.test"]
    assert exported == expected
    assert manifest["purpose"] == "automated-check"
    assert manifest["data_label"] == "SYNTHETIC"
    assert manifest["row_count"] == 3
    assert manifest["export_sha256"] == hashlib.sha256((output / "events.json").read_bytes()).hexdigest()
    csv_rows = parse_events((output / "events.csv").read_bytes(), "csv")
    assert [normalize_event(row) for row in csv_rows] == [normalize_event(row) for row in exported]
    db = str(tmp_path / "roundtrip.db")
    assert import_events(exported, db) == {"added": 3, "already_present": 0, "groups": 2}
    assert import_events(csv_rows, db)["already_present"] == 3
    assert sorted(len(group["events"]) for group in list_alert_groups(db)) == [1, 2]
    with pytest.raises(FileExistsError):
        run_query(output, purpose="automated-check")
