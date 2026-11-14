"""Streamlit smoke coverage using temporary SQLite and no API provider."""
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from patchwise.core.alert_triage import get_investigation, import_events, list_alert_groups

ROOT = Path(__file__).resolve().parents[1]


def test_manual_review_and_navigation_without_ai_key(tmp_path, monkeypatch):
    db = str(tmp_path / "ui.db")
    monkeypatch.setenv("PATCHWISE_DB_PATH", db)
    monkeypatch.setenv("PATCHWISE_AI_API_KEY", "")
    rows = json.loads((ROOT / "examples/identity-network-events.json").read_text())
    import_events(rows, db)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Alert triage").run()
    assert not app.exception
    # The first group is the incomplete case; preserve and review it manually.
    app.text_area[0].set_value("Evidence is incomplete (incomplete-004).")
    app.text_area[1].set_value("11:00 UTC incomplete-004 received")
    app.multiselect[0].set_value(["incomplete-004"])
    app.text_area[2].set_value("The evidence object is empty (incomplete-004).")
    app.text_area[3].set_value("Need sign-in outcome, source IP and MFA context.")
    app.text_area[4].set_value("Do not escalate until more evidence is available.")
    app.checkbox[0].set_value(True)
    next(button for button in app.button if button.label == "Save investigation").click().run()
    assert not app.exception
    group = next(group for group in list_alert_groups(db) if group["events"][0]["event_id"] == "incomplete-004")
    assert get_investigation(group["group_id"], db)["reviewed"]
    assert any(button.label == "Download reviewed Jira draft" for button in app.get("download_button"))
    assert next(button for button in app.button if button.label == "Request AI draft").disabled
    for page in ("Triage benchmark", "Reports", "Findings", "Investigation", "Overview"):
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, page


def test_benchmark_timer_scoring_and_existing_project_reports(tmp_path, monkeypatch):
    from patchwise.core.alert_triage import save_investigation
    from patchwise.core.benchmark import benchmark_cases, list_runs
    from patchwise.core.repository_manager import register_project, save_findings

    db = str(tmp_path / "timer.db")
    monkeypatch.setenv("PATCHWISE_DB_PATH", db)
    monkeypatch.setenv("PATCHWISE_AI_API_KEY", "")
    rows = json.loads((ROOT / "examples/identity-network-events.json").read_text())
    import_events(rows, db)
    project_dir = tmp_path / "repo"
    project_dir.mkdir()
    project = register_project(project_dir, db)
    save_findings(project["id"], [{"title": "Synthetic scanner result", "severity": "high", "scanner": "bandit"}], db)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    app.sidebar.radio[0].set_value("Triage benchmark").run()
    app.selectbox[0].set_value(benchmark_cases()[0][3])
    app.text_input[0].set_value("ui-test")
    next(button for button in app.button if button.label == "Start case timer").click().run()
    assert not app.exception
    next(button for button in app.button if button.label == "Stop timer after reviewed record").click().run()
    assert app.error  # Cannot stop with an unreviewed case.
    group = next(group for group in list_alert_groups(db) if group["events"][0]["event_id"] == "incomplete-004")
    save_investigation(group["group_id"], {"summary": "Incomplete case", "timeline_notes": "11:00 UTC incomplete-004",
        "supporting_evidence": "Empty object (incomplete-004)", "evidence_ids": ["incomplete-004"],
        "missing_context": "Need outcome and MFA", "disposition": "Inconclusive",
        "escalation_rationale": "Await context", "reviewed": True}, db)
    app.sidebar.radio[0].set_value("Overview").run()
    app.sidebar.radio[0].set_value("Triage benchmark").run()
    next(button for button in app.button if button.label == "Stop timer after reviewed record").click().run()
    assert not app.exception
    app.number_input[0].set_value(0)
    app.number_input[1].set_value(0)
    next(button for button in app.button if button.label == "Save benchmark result").click().run()
    assert not app.exception
    saved = list_runs(db)
    assert len(saved) == 1
    assert saved[0]["elapsed_seconds"] > 0
    app.sidebar.radio[0].set_value("Reports").run()
    assert not app.exception
    labels = {button.label for button in app.get("download_button")}
    assert {"Download markdown report", "Download JSON report", "Download alert triage report"}.issubset(labels)


def test_remove_scanned_project_from_projects_page(tmp_path, monkeypatch):
    from patchwise.core.repository_manager import (
        list_findings, list_projects, list_scan_records, register_project, save_findings, save_scan_record,
    )

    db = str(tmp_path / "remove-ui.db")
    monkeypatch.setenv("PATCHWISE_DB_PATH", db)
    monkeypatch.setenv("PATCHWISE_AI_API_KEY", "")
    project_dir = tmp_path / "scanned-repo"
    project_dir.mkdir()
    source = project_dir / "app.py"
    source.write_text("print('keep me')\n")
    project = register_project(project_dir, db)
    save_findings(project["id"], [{"title": f"Test finding {index}"} for index in range(3)], db)
    save_scan_record(project["id"], "completed", "Three findings", db)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    app.sidebar.radio[0].set_value("Projects").run()
    next(button for button in app.button if button.key == f"select_{project['id']}").click().run()
    assert app.session_state["selected_project_id"] == project["id"]
    next(button for button in app.button if button.key == f"remove_{project['id']}").click().run()
    assert not app.exception
    assert not list_projects(db)
    assert not list_findings(db_path=db)
    assert not list_scan_records(db_path=db)
    assert "selected_project_id" not in app.session_state
    assert source.read_text() == "print('keep me')\n"


def test_ai_claim_shows_full_cited_event_beside_it(tmp_path, monkeypatch):
    from patchwise.ai.alert_drafting import create_draft
    from patchwise.core.config import AppConfig

    db = str(tmp_path / "claim-comparison.db")
    monkeypatch.setenv("PATCHWISE_DB_PATH", db)
    monkeypatch.setenv("PATCHWISE_AI_API_KEY", "")
    rows = json.loads((ROOT / "examples/identity-network-events.json").read_text())[:2]
    import_events(rows, db)
    group_id = list_alert_groups(db)[0]["group_id"]
    claim = "MOCK TEST DRAFT: the event reports MFA false."
    monkeypatch.setattr("patchwise.ai.alert_drafting.request_draft", lambda *args: {
        "claims": [{"text": claim, "event_ids": ["signin-001"]}],
        "follow_up_questions": ["Was this expected?"], "missing_evidence": ["Independent confirmation missing"],
    })
    create_draft(group_id, ["signin-001"], AppConfig(ai_api_key="test-only"), db)
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    app.sidebar.radio[0].set_value("Alert triage").run()
    assert not app.exception
    columns = app.get("column")
    assert claim in columns[0].text[0].value
    cited_event = json.loads(columns[1].json[0].value)
    assert cited_event["event_id"] == "signin-001"
    # Includes the local message omitted from the minimized AI payload.
    assert cited_event["evidence"] == rows[0]["evidence"]
