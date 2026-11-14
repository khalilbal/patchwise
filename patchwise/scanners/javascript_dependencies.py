from __future__ import annotations

import json
from pathlib import Path

from patchwise.scanners.base import run_command


def scan_npm_audit(project_dir: str | Path, timeout: int = 120) -> list[dict]:
    root = Path(project_dir)
    if not root.exists() or not (root / "package.json").exists():
        return []

    command = ["npm", "audit", "--json", "--audit-level=low"]
    try:
        result = run_command(command, root, timeout=timeout)
    except Exception:
        return []

    if not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    findings: list[dict] = []
    vulnerabilities = payload.get("vulnerabilities") or {}
    for name, value in vulnerabilities.items():
        details = value or {}
        severity = (details.get("severity") or "medium").lower()
        via = details.get("via") or []
        desc = ""
        if isinstance(via, list):
            desc = " | ".join(str(item) for item in via[:3])
        elif isinstance(via, dict):
            desc = via.get("title") or via.get("url") or "npm advisory"
        findings.append(
            {
                "title": f"{name} vulnerable",
                "description": desc or "npm audit detected a known dependency issue.",
                "severity": severity,
                "scanner": "npm-audit",
                "source": f"{name}",
                "package": name,
                "version": str(details.get("range") or "unknown"),
                "cvss_score": 7.5,
                "fix_available": bool(details.get("fixAvailable")),
                "direct_dependency": True,
                "cve": None,
            }
        )
    return findings
