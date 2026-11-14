from __future__ import annotations

import streamlit as st

from patchwise.core.repository_manager import get_activity_logs, list_findings, list_projects, log_activity, update_finding_status


def render_investigation() -> None:
    st.title("Investigation")
    projects = list_projects()
    if not projects:
        st.info("Register a project before investigating findings.")
        return

    project = st.selectbox("Project", options=projects, format_func=lambda item: item.name)
    findings = list_findings(project.id)
    if not findings:
        st.info("No findings saved for this project yet.")
        return

    finding = st.selectbox("Finding", options=findings, format_func=lambda item: item.title)
    st.write(f"Description: {finding.description}")
    st.write(f"Severity: {finding.severity}")
    st.write(f"Scanner: {finding.scanner}")
    st.write(f"Source: {finding.source}")

    new_status = st.selectbox("Finding status", ["Open", "Investigating", "Fix Planned", "Verification Pending", "Resolved", "False Positive", "Risk Accepted"], index=["Open", "Investigating", "Fix Planned", "Verification Pending", "Resolved", "False Positive", "Risk Accepted"].index(finding.status) if finding.status in ["Open", "Investigating", "Fix Planned", "Verification Pending", "Resolved", "False Positive", "Risk Accepted"] else 0)
    if st.button("Save status"):
        update_finding_status(finding.id, new_status)
        log_activity(project.id, finding.id, "status-change", f"Status set to {new_status}")
        st.success(f"Updated {finding.title} to {new_status}")

    notes = st.text_area("Investigation notes", value="")
    if st.button("Save note"):
        log_activity(project.id, finding.id, "note", notes)
        st.success("Note saved to activity log.")

    st.subheader("Activity log")
    for entry in get_activity_logs(project_id=project.id, finding_id=finding.id):
        st.write(f"- {entry.created_at}: {entry.action} — {entry.details}")
