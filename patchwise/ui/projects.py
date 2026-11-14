from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from patchwise.core.repository_manager import (
    detect_manifests,
    get_project_by_id,
    is_git_repo,
    list_projects,
    register_project,
    remove_project,
    validate_repository_path,
)
from patchwise.core.scan_orchestrator import run_scan


def render_projects() -> None:
    st.title("Projects")
    project_path = st.text_input("Local project folder or file", key="project_path")
    if st.button("Register repository", key="register_repository"):
        try:
            validated = validate_repository_path(project_path)
            project = register_project(validated)
            st.success(f"Registered {project['name']} at {project['path']}")
            st.write("Detected manifests:", detect_manifests(validated))
            st.write("Git repository:", is_git_repo(validated))
        except Exception as exc:
            st.error(str(exc))

    projects = list_projects()
    if projects:
        st.subheader("Registered projects")
        st.caption("Removing a project deletes its saved scanner findings, scan history and investigation records. Source files remain on disk.")
        for project in projects:
            with st.container():
                st.write(f"{project.name} — {project.path}")
                col1, col2 = st.columns([1, 1])
                if col1.button(f"Select {project.name}", key=f"select_{project.id}"):
                    st.session_state["selected_project_id"] = project.id
                if col2.button(f"Scan {project.name}", key=f"scan_{project.id}"):
                    result = run_scan(project.path)
                    st.success(f"Scan completed for {project.name}: {result['summary']['finding_count']} findings")
                if st.button(f"Remove {project.name}", key=f"remove_{project.id}"):
                    try:
                        remove_project(project.id)
                    except SQLAlchemyError:
                        st.error("Could not remove this project. No changes were saved; please try again.")
                    else:
                        if st.session_state.get("selected_project_id") == project.id:
                            st.session_state.pop("selected_project_id", None)
                        st.rerun()
                st.caption(f"Git: {project.is_git} | Language: {project.language}")
    else:
        st.info("No projects are currently registered. Add a local directory or repo above.")

    uploaded = st.file_uploader("Optional source file preview", type=["py", "js", "ts", "txt"], accept_multiple_files=False)
    if uploaded is not None:
        st.write("Selected file:", uploaded.name)
        st.info("This preview is for display only. Use the project folder path above for a real scan.")

    selected_project_id = st.session_state.get("selected_project_id")
    if selected_project_id is not None:
        project = get_project_by_id(selected_project_id)
        if project is not None:
            st.write("Selected project:", project.path)
