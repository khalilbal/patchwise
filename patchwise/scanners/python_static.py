from __future__ import annotations

import json
from pathlib import Path

from patchwise.scanners.base import run_command


def scan_bandit(project_dir: str | Path, timeout: int = 120) -> list[dict]:
    root = Path(project_dir)
    if not root.exists():
        return []

    findings: list[dict] = []
    command = ["bandit", "-r", str(root), "-f", "json", "-q"]
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

    for issue in payload.get("results", []):
        filename = issue.get("filename") or "unknown"
        line = issue.get("line_number") or 0
        findings.append(
            {
                "title": issue.get("test_id") or "Bandit finding",
                "description": issue.get("issue_text") or "Security issue detected by Bandit.",
                "severity": (issue.get("issue_severity") or "medium").lower(),
                "scanner": "bandit",
                "source": f"{filename}:{line}",
                "package": filename,
                "path": filename,
                "line": line,
                "cvss_score": 6.5,
                "fix_available": False,
                "direct_dependency": False,
            }
        )
    return findings
