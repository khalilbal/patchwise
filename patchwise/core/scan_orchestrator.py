from __future__ import annotations

from pathlib import Path

from patchwise.core.finding_tracker import dedupe_findings
from patchwise.core.repository_manager import (
    detect_manifests,
    list_findings,
    register_project,
    save_findings,
    save_scan_record,
    validate_repository_path,
)
from patchwise.scanners.javascript_dependencies import scan_npm_audit
from patchwise.scanners.python_dependencies import scan_pip_audit
from patchwise.scanners.python_static import scan_bandit


def run_scan(project_path: str | Path, timeout: int = 120, db_path: str | None = None) -> dict:
    root = validate_repository_path(project_path)
    project = register_project(root, db_path=db_path)
    project_id = project["id"]
    manifests = detect_manifests(root)
    findings: list[dict] = []
    errors: list[str] = []

    if any(name in manifests for name in ["requirements.txt", "pyproject.toml"]):
        try:
            findings.extend(scan_pip_audit(root, timeout=timeout))
        except Exception as exc:  # pragma: no cover - defensive guard
            errors.append(f"pip-audit failure: {exc}")

    if any(name in manifests for name in ["package.json", "package-lock.json"]):
        try:
            findings.extend(scan_npm_audit(root, timeout=timeout))
        except Exception as exc:  # pragma: no cover - defensive guard
            errors.append(f"npm audit failure: {exc}")

    if any(root.rglob("*.py")):
        try:
            findings.extend(scan_bandit(root, timeout=timeout))
        except Exception as exc:  # pragma: no cover - defensive guard
            errors.append(f"Bandit failure: {exc}")

    deduped = dedupe_findings(findings)
    save_scan_record(project_id, "completed", f"Scan completed for {root.name}: {len(deduped)} findings", db_path=db_path)
    save_findings(project_id, deduped, db_path=db_path)
    summary = {
        "project_id": project_id,
        "project": str(root),
        "manifest_count": len(manifests),
        "finding_count": len(deduped),
        "errors": errors,
    }
    return {
        "project_id": project_id,
        "project": project,
        "findings": deduped,
        "stored_findings": list_findings(project_id=project_id, db_path=db_path),
        "manifests": manifests,
        "errors": errors,
        "summary": summary,
    }
