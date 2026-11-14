from __future__ import annotations

import json
from pathlib import Path

from patchwise.scanners.base import run_command


def _parse_pip_audit_payload(payload: object) -> list[dict]:
    findings: list[dict] = []
    if isinstance(payload, list):
        dependencies = payload
    elif isinstance(payload, dict):
        dependencies = payload.get("dependencies") or payload.get("vulnerabilities") or []
    else:
        return findings

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        name = dependency.get("name") or dependency.get("package") or "unknown"
        version = dependency.get("version") or dependency.get("installed_version") or "unknown"
        vulns = dependency.get("vulns") or dependency.get("vulnerabilities") or []
        if not vulns and dependency.get("id"):
            vulns = [dependency]
        for vuln in vulns:
            if isinstance(vuln, dict):
                findings.append(
                    {
                        "title": vuln.get("id") or f"Vulnerability in {name}",
                        "description": vuln.get("description") or vuln.get("summary") or "Dependency vulnerability identified.",
                        "severity": (vuln.get("severity") or "medium").lower(),
                        "scanner": "pip-audit",
                        "source": f"{name}:{version}",
                        "package": name,
                        "version": version,
                        "cvss_score": 7.5,
                        "fix_available": bool(vuln.get("fix_versions") or vuln.get("fix_version")),
                        "direct_dependency": True,
                        "cve": vuln.get("aliases") or vuln.get("id"),
                    }
                )
    return findings


def scan_pip_audit(project_dir: str | Path, timeout: int = 120) -> list[dict]:
    root = Path(project_dir)
    if not root.exists():
        return []

    requirements = root / "requirements.txt"
    pyproject = root / "pyproject.toml"
    if requirements.exists():
        cmd = ["pip-audit", "-r", str(requirements), "--format", "json"]
    elif pyproject.exists():
        cmd = ["pip-audit", "--path", str(root), "--format", "json"]
    else:
        return []

    try:
        result = run_command(cmd, root, timeout=timeout)
    except Exception:
        return []

    if not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return _parse_pip_audit_payload(payload)
