from __future__ import annotations

from pathlib import Path
import json
from types import SimpleNamespace

import pytest

from patchwise.core.repository_manager import list_findings, list_projects, register_project
from patchwise.core.scan_orchestrator import run_scan


@pytest.fixture(autouse=True)
def dependency_audit_fixture(monkeypatch):
    """Keep orchestration/persistence tests independent of the live package index."""
    payload = {"dependencies": [{"name": "requests", "version": "2.31.0", "vulns": [{
        "id": "PYSEC-lab", "aliases": ["CVE-2024-35195"],
        "description": "Synthetic audit result for persistence testing", "fix_versions": ["2.32.0"]
    }]}]}
    monkeypatch.setattr("patchwise.scanners.python_dependencies.run_command",
                        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(payload)))


def test_scan_detects_bad_python_pattern_in_sample_repo(tmp_path):
    project = tmp_path / "vulnerable-app"
    project.mkdir()
    (project / "app.py").write_text(
        "import subprocess\n"
        "subprocess.call('ls -la', shell=True)\n",
        encoding="utf-8",
    )
    (project / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    result = run_scan(project, timeout=60, db_path=str(tmp_path / "patchwise.db"))

    assert result["summary"]["finding_count"] > 0
    assert any(item["scanner"] == "bandit" for item in result["findings"])
    registered = list_projects(db_path=str(tmp_path / "patchwise.db"))
    assert len(registered) == 1
    assert list_findings(project_id=registered[0].id, db_path=str(tmp_path / "patchwise.db"))


def test_project_and_findings_persist_across_database_sessions(tmp_path):
    db_path = str(tmp_path / "persist.db")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    (project_dir / "app.py").write_text("import os\nprint(os.getcwd())\n", encoding="utf-8")

    project = register_project(project_dir, db_path=db_path)
    result = run_scan(project_dir, timeout=60, db_path=db_path)

    assert project["id"] is not None
    assert result["project_id"] == project["id"]
    assert list_projects(db_path=db_path)
    assert list_findings(project_id=project["id"], db_path=db_path)


def test_all_three_scanner_results_remain_persisted(tmp_path, monkeypatch):
    project = tmp_path / "mixed-project"
    project.mkdir()
    (project / "requirements.txt").write_text("requests==2.31.0\n")
    (project / "package.json").write_text('{"name":"lab","dependencies":{"lab-package":"1.0.0"}}')
    (project / "app.py").write_text("import subprocess\nsubprocess.call('ls', shell=True)\n")
    npm_payload = {"vulnerabilities": {"lab-package": {"severity": "high", "range": "1.0.0",
                    "via": [{"title": "Synthetic npm advisory"}], "fixAvailable": True}}}
    monkeypatch.setattr("patchwise.scanners.javascript_dependencies.run_command",
                        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(npm_payload)))
    db = str(tmp_path / "mixed.db")
    result = run_scan(project, db_path=db)
    assert not result["errors"]
    assert {finding.scanner for finding in result["stored_findings"]} == {"bandit", "pip-audit", "npm-audit"}
    assert any(finding.cve == "CVE-2024-35195" for finding in result["stored_findings"])
