from pathlib import Path

import pytest

from patchwise.core.repository_manager import validate_repository_path


def test_validate_repository_path_accepts_existing_directory(tmp_path):
    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()

    resolved = validate_repository_path(project_dir)

    assert resolved == project_dir.resolve()


def test_validate_repository_path_rejects_missing_directory(tmp_path):
    missing = tmp_path / "missing-project"

    with pytest.raises(FileNotFoundError):
        validate_repository_path(missing)


def test_validate_repository_path_rejects_traversal():
    with pytest.raises(ValueError):
        validate_repository_path("../../etc")


@pytest.fixture(params=[False, True], ids=["sqlite-default", "foreign-keys-enabled"])
def populated_project_database(tmp_path, monkeypatch, request):
    """Two scanned projects, complete finding history, and unrelated alert data."""
    from sqlalchemy import event
    from sqlalchemy.orm import sessionmaker

    from patchwise.core import repository_manager
    from patchwise.core.alert_triage import import_events, list_alert_groups, save_investigation
    from patchwise.core.database import get_engine, init_db
    from patchwise.core.models import ActivityLog, Finding, FindingEvidence, Project, RemediationRecord, ScanRecord

    db = str(tmp_path / "removal.db")
    init_db(db)
    engine = get_engine(db)
    if request.param:
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(repository_manager, "get_session_factory", lambda db_path=None: factory)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / "app.py"
    source_file.write_text("print('preserve this source')\n")
    with factory() as session:
        removed = Project(name="remove-me", path=str(source_dir))
        kept = Project(name="keep-me", path=str(tmp_path / "other-source"))
        session.add_all([removed, kept])
        session.flush()
        removed_id, kept_id = removed.id, kept.id
        findings = [Finding(project_id=removed.id, title=f"Finding {index}") for index in range(3)]
        kept_finding = Finding(project_id=kept.id, title="Keep this finding")
        session.add_all([*findings, kept_finding])
        session.flush()
        for finding in [*findings, kept_finding]:
            session.add_all([
                FindingEvidence(finding_id=finding.id, evidence_value="scanner evidence"),
                RemediationRecord(finding_id=finding.id, proposed_fix="investigate"),
                ActivityLog(project_id=finding.project_id, finding_id=finding.id, action="note"),
            ])
        session.add_all([
            ScanRecord(project_id=removed.id, summary="Remove scan"),
            ScanRecord(project_id=kept.id, summary="Keep scan"),
            ActivityLog(project_id=removed.id, action="project-only"),
            ActivityLog(finding_id=findings[0].id, action="finding-only"),
            ActivityLog(action="global-note"),
        ])
        session.commit()
    import_events([{"event_id": "preserve-alert", "source": "lab"}], db)
    group_id = list_alert_groups(db)[0]["group_id"]
    save_investigation(group_id, {"summary": "Keep alert investigation", "disposition": "Investigating",
                                  "evidence_ids": ["preserve-alert"]}, db)
    yield db, factory, removed_id, kept_id, source_file
    engine.dispose()


def test_remove_scanned_project_cleans_dependents_and_preserves_other_data(populated_project_database):
    from sqlalchemy import select

    from patchwise.core.alert_triage import get_investigation, list_alert_groups
    from patchwise.core.models import ActivityLog, Finding, FindingEvidence, Project, RemediationRecord, ScanRecord
    from patchwise.core.repository_manager import remove_project

    db, factory, removed_id, kept_id, source_file = populated_project_database
    remove_project(removed_id, db)
    remove_project(removed_id, db)  # A repeated click/missing project is harmless.
    with factory() as session:
        assert session.get(Project, removed_id) is None
        assert session.get(Project, kept_id) is not None
        findings = session.scalars(select(Finding)).all()
        assert len(findings) == 1 and findings[0].project_id == kept_id
        for model in (FindingEvidence, RemediationRecord):
            records = session.scalars(select(model)).all()
            assert len(records) == 1 and records[0].finding_id == findings[0].id
        scans = session.scalars(select(ScanRecord)).all()
        assert len(scans) == 1 and scans[0].project_id == kept_id
        logs = session.scalars(select(ActivityLog)).all()
        assert len(logs) == 2
        assert {log.action for log in logs} == {"note", "global-note"}
        assert all(log.project_id in (None, kept_id) for log in logs)
    alert = list_alert_groups(db)[0]
    assert alert["events"][0]["event_id"] == "preserve-alert"
    assert get_investigation(alert["group_id"], db)["summary"] == "Keep alert investigation"
    assert source_file.read_text() == "print('preserve this source')\n"


def test_remove_project_failure_rolls_back_all_records(populated_project_database):
    from sqlalchemy import event, func, select
    from sqlalchemy.exc import OperationalError

    from patchwise.core.models import ActivityLog, Finding, FindingEvidence, Project, RemediationRecord, ScanRecord
    from patchwise.core.repository_manager import remove_project

    db, factory, removed_id, _kept_id, _source = populated_project_database
    engine = factory.kw["bind"]
    models = (Project, Finding, FindingEvidence, RemediationRecord, ScanRecord, ActivityLog)
    def counts():
        with factory() as session:
            return [session.scalar(select(func.count()).select_from(model)) for model in models]
    before = counts()
    # Abort the final deletion after child DELETEs have run to test atomicity.
    def fail_parent_delete(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().startswith("DELETE FROM projects"):
            raise OperationalError(statement, {}, RuntimeError("simulated database failure"))
    event.listen(engine, "before_cursor_execute", fail_parent_delete)
    try:
        with pytest.raises(OperationalError):
            remove_project(removed_id, db)
    finally:
        event.remove(engine, "before_cursor_execute", fail_parent_delete)
    assert counts() == before
