from __future__ import annotations

import streamlit as st

from patchwise.core.repository_manager import list_findings, list_projects


def render_findings() -> None:
    st.title("Findings")
    projects = list_projects()
    project_map = {project.id: project.name for project in projects}
    severity = st.selectbox("Severity", ["All", "Critical", "High", "Medium", "Low"])

    findings = list_findings()
    if severity != "All":
        findings = [item for item in findings if item.severity.lower() == severity.lower()]

    if not findings:
        st.info("No findings yet. Register a repository and trigger a scan to populate the results view.")
        return

    for finding in findings:
        project_name = project_map.get(finding.project_id, "Unknown")
        st.markdown(f"### {finding.title} ({finding.severity})")
        st.write(f"Project: {project_name}")
        st.write(f"Source: {finding.source}")
        st.write(f"Description: {finding.description}")
        st.write(f"Status: {finding.status}")
        st.write(f"Package: {finding.package_name or 'n/a'} | Version: {finding.package_version or 'n/a'}")
        st.divider()
