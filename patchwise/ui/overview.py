from __future__ import annotations

import streamlit as st

from patchwise.core.repository_manager import list_findings, list_projects, list_scan_records


def render_overview() -> None:
    projects = list_projects()
    findings = list_findings()
    scans = list_scan_records()

    st.title("Overview")
    st.write("Patchwise monitors local repositories for dependency and code security issues without uploading source code to external services.")
    col1, col2, col3 = st.columns(3)
    col1.metric("Projects tracked", len(projects))
    col2.metric("Unresolved findings", sum(1 for item in findings if item.status not in {"resolved", "false positive", "risk accepted"}))
    col3.metric("Last scan", scans[0].scanned_at.strftime("%Y-%m-%d %H:%M") if scans else "Never")

    if projects:
        st.subheader("Recent project activity")
        for project in projects[:5]:
            project_findings = list_findings(project.id)
            st.write(f"- {project.name}: {len(project_findings)} saved findings")
    else:
        st.caption("Use the Projects page to add a local folder or Git repository and start a scan.")
