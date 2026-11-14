from __future__ import annotations

import json

import streamlit as st

from patchwise.core.repository_manager import list_findings, list_projects, list_scan_records
from patchwise.core.alert_triage import investigation_snapshot, list_alert_groups
from patchwise.ai.alert_drafting import list_drafts
from patchwise.core.benchmark import export_csv, list_runs


def render_reports() -> None:
    st.title("Reports")
    groups = list_alert_groups()
    if groups:
        triage = [{**investigation_snapshot(group["group_id"]), "ai_drafts": list_drafts(group["group_id"])} for group in groups]
        st.download_button("Download alert triage report", data=json.dumps(triage, indent=2),
                           file_name="alert-triage-report.json", mime="application/json")
    st.download_button("Download triage benchmark results", data=export_csv(list_runs()),
                       file_name="triage-benchmark.csv", mime="text/csv")
    projects = list_projects()
    if not projects:
        st.info("No projects have been registered yet, so there is no stored report data to export.")
        return

    snapshot = {
        "projects": [
            {
                "name": project.name,
                "path": project.path,
                "language": project.language,
                "last_scanned_at": project.last_scanned_at.isoformat() if project.last_scanned_at else None,
                "findings": [
                    {
                        "title": finding.title,
                        "severity": finding.severity,
                        "status": finding.status,
                        "scanner": finding.scanner,
                        "source": finding.source,
                        "description": finding.description,
                    }
                    for finding in list_findings(project.id)
                ],
            }
            for project in projects
        ],
        "scan_history": [
            {"project_id": record.project_id, "status": record.status, "summary": record.summary, "scanned_at": record.scanned_at.isoformat()}
            for record in list_scan_records()
        ],
    }

    markdown = "# Patchwise report\n\n"
    for project in projects:
        markdown += f"## {project.name}\n"
        project_findings = list_findings(project.id)
        if not project_findings:
            markdown += "No findings\n\n"
        else:
            for finding in project_findings:
                markdown += f"- {finding.title} ({finding.severity}) — {finding.status}\n"
            markdown += "\n"

    st.download_button("Download markdown report", data=markdown, file_name="patchwise-report.md")
    st.download_button("Download JSON report", data=json.dumps(snapshot, indent=2), file_name="patchwise-report.json")
