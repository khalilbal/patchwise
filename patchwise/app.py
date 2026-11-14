from __future__ import annotations

import streamlit as st

from patchwise.core.config import load_config
from patchwise.core.repository_manager import list_projects, register_project
from patchwise.core.scan_orchestrator import run_scan
from patchwise.ui import (
    alerts,
    benchmark,
    findings,
    investigation,
    overview,
    projects,
    reports,
    settings,
)


def main() -> None:
    load_config()
    st.set_page_config(page_title="Patchwise", page_icon="🛡️", layout="wide")

    st.sidebar.title("Patchwise")
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Projects", "Findings", "Investigation", "Alert triage", "Triage benchmark", "Reports", "Settings"],
    )

    if page == "Overview":
        overview.render_overview()
    elif page == "Projects":
        projects.render_projects()
    elif page == "Findings":
        findings.render_findings()
    elif page == "Investigation":
        investigation.render_investigation()
    elif page == "Alert triage":
        alerts.render_alerts()
    elif page == "Triage benchmark":
        benchmark.render_benchmark()
    elif page == "Reports":
        reports.render_reports()
    else:
        settings.render_settings()
