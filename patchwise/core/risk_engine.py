from __future__ import annotations

from typing import Any


def calculate_priority(finding: dict[str, Any]) -> tuple[int, str]:
    score = float(finding.get("cvss_score") or 0.0)
    if finding.get("is_kev"):
        score += 4.0
    if finding.get("fix_available"):
        score -= 0.5
    if finding.get("direct_dependency"):
        score += 1.0

    if score >= 8.5:
        return 1, "Critical"
    if score >= 6.5:
        return 2, "High"
    if score >= 4.0:
        return 3, "Medium"
    return 4, "Low"


def priority_rationale(finding: dict[str, Any]) -> str:
    reasons = []
    if finding.get("is_kev"):
        reasons.append("listed in CISA KEV")
    if finding.get("direct_dependency"):
        reasons.append("direct dependency")
    if finding.get("fix_available"):
        reasons.append("remediation available")
    score = finding.get("cvss_score")
    if score is not None:
        reasons.append(f"CVSS {score}")
    if not reasons:
        return "Scanner severity and limited evidence were used to flag the issue."
    return ", ".join(reasons)
