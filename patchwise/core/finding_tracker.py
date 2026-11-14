from __future__ import annotations

from collections import OrderedDict
from typing import Any


def normalize_finding(raw: dict[str, Any]) -> dict[str, Any]:
    cve = raw.get("cve") or raw.get("id") or None
    if isinstance(cve, list):
        cve = ", ".join(str(item) for item in cve[:3])

    normalized = {
        "title": raw.get("title") or raw.get("package") or "Unnamed finding",
        "description": raw.get("description") or raw.get("summary") or "",
        "severity": (raw.get("severity") or "unknown").lower(),
        "scanner": raw.get("scanner") or "unknown",
        "source": raw.get("source") or "",
        "cve": cve,
        "package": raw.get("package") or raw.get("package_name") or "",
        "version": raw.get("version") or raw.get("package_version") or "",
        "fix_available": bool(raw.get("fix_available")),
        "is_kev": bool(raw.get("is_kev")),
        "direct_dependency": bool(raw.get("direct_dependency")),
        "cvss_score": raw.get("cvss_score"),
        "path": raw.get("path") or "",
        "line": raw.get("line") or 0,
    }
    return normalized


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
    for finding in findings:
        normalized = normalize_finding(finding)
        key = (
            normalized["scanner"],
            normalized["package"],
            str(normalized["cve"] or normalized["source"]),
            normalized["title"],
        )
        if key not in seen:
            seen[key] = normalized
    return list(seen.values())


def compare_findings(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, list[str]]:
    prev_ids = {((f.get("scanner"), f.get("package"), f.get("cve") or f.get("source"), f.get("title"))) for f in previous}
    cur_ids = {((f.get("scanner"), f.get("package"), f.get("cve") or f.get("source"), f.get("title"))) for f in current}
    new = sorted([str(item) for item in cur_ids - prev_ids])
    resolved = sorted([str(item) for item in prev_ids - cur_ids])
    return {"new": new, "resolved": resolved}
