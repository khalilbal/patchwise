from __future__ import annotations


def recommend_remediation(finding: dict) -> dict:
    package = finding.get("package") or finding.get("package_name") or "dependency"
    version = finding.get("version") or finding.get("package_version") or "current version"
    fixed = finding.get("fixed_version") or "latest patched release"
    source = finding.get("source") or "scanner output"
    recommendation = (
        f"Upgrade {package} from {version} to {fixed} or to the latest patched version supported by your project. "
        f"Review compatibility changes and test the affected dependency path before deployment."
    )
    if "bandit" in source.lower() or "security" in source.lower():
        recommendation = (
            f"Review the flagged code path in {source} and apply the suggested secure coding fix. "
            "Validate the affected input handling and confirm the fix with a focused security rescan."
        )
    return {"summary": recommendation, "risk": "manual review required", "verification": "Rescan and test only the affected workflow."}
