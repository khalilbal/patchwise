import csv
import io

import pytest

from patchwise.core.benchmark import benchmark_cases, export_csv, list_runs, save_run, summarize


def row(case_id, workflow, seconds):
    return {"participant": "test-participant", "case_id": case_id, "workflow": workflow,
            "case_set_sha256": benchmark_cases()[1], "elapsed_seconds": seconds,
            "evidence_missed": 0, "unsupported_claims": 0, "ai_mistake": "", "analyst_correction": ""}


def test_paired_medians_exclude_incomplete_pairs():
    rows = [row("suspicious-signin", "manual", 100), row("suspicious-signin", "ai-assisted", 80),
            row("benign-lookalike", "manual", 200), row("benign-lookalike", "ai-assisted", 100),
            row("missing-evidence", "manual", 900)]
    summary = summarize(rows)
    assert summary["paired_cases"] == 2
    assert summary["unpaired_cases_excluded"] == 1
    assert summary["manual_median_seconds"] == 150
    assert summary["ai_assisted_median_seconds"] == 90
    assert summary["change_seconds"] == -60
    assert summary["change_percent"] == -40
    assert summary["median_paired_change_seconds"] == -60
    assert summarize([]) == {"paired_cases": 0, "unpaired_cases_excluded": 0}


def test_results_are_empty_until_entered_and_csv_round_trips(tmp_path):
    db = str(tmp_path / "bench.db")
    assert list_runs(db) == []
    assert len(export_csv([]).splitlines()) == 1
    measured = row("suspicious-signin", "manual", 100)
    save_run(measured, db)
    assert len(list_runs(db)) == 1
    loaded = list(csv.DictReader(io.StringIO(export_csv(list_runs(db)))))
    assert summarize(loaded)["unpaired_cases_excluded"] == 1
    with pytest.raises(ValueError, match="already recorded"):
        save_run(measured, db)


@pytest.mark.parametrize("changes", [
    {"elapsed_seconds": float("nan")}, {"elapsed_seconds": -1}, {"evidence_missed": None},
    {"evidence_missed": 5}, {"unsupported_claims": -1}, {"case_set_sha256": "wrong"},
    {"ai_mistake": "A real ID accompanied a false claim", "analyst_correction": ""},
])
def test_invalid_or_unentered_measurements_rejected(changes, tmp_path):
    with pytest.raises(ValueError):
        save_run({**row("suspicious-signin", "manual", 100), **changes}, str(tmp_path / "bench.db"))


def test_csv_neutralizes_spreadsheet_formulas():
    csv_text = export_csv([{**row("suspicious-signin", "manual", 100), "ai_mistake": "=HYPERLINK(\"example\")"}])
    assert "'=HYPERLINK" in csv_text
