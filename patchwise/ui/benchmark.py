from __future__ import annotations

import json
import time

import streamlit as st

from patchwise.ai.alert_drafting import list_drafts
from patchwise.core.alert_triage import canonical, get_group_events, get_investigation, group_id_for, normalize_event
from patchwise.core.benchmark import EXAMPLES, benchmark_cases, export_csv, list_runs, save_run, summarize


def render_benchmark() -> None:
    st.title("Triage benchmark")
    st.write("Run the same four bundled cases with manual and AI-assisted triage. Score the initial draft, "
             "then record corrections and complete the reviewed record. No results are prefilled.")
    st.caption("Use a participant/session pseudonym, counterbalance workflow order, and keep the same case dataset. "
               "Consult docs/benchmark.md for the rubric and controls against learning effects.")
    cases, fingerprint = benchmark_cases()
    case = st.selectbox("Benchmark case", cases, format_func=lambda item: item["case_id"])
    participant = st.text_input("Participant/session pseudonym")
    workflow = st.selectbox("Workflow", ["manual", "ai-assisted"])
    st.code(f"Case set SHA-256: {fingerprint}")
    active = st.session_state.get("triage_benchmark_active")
    if st.button("Start case timer", disabled=active is not None):
        try:
            fixtures = json.loads((EXAMPLES / "identity-network-events.json").read_text())
            expected = [normalize_event(row) for row in fixtures if row["event_id"] in case["event_ids"]]
            group_id = group_id_for(expected[0])
            actual = get_group_events(group_id)
            if sorted(canonical(event) for event in actual) != sorted(canonical(event) for event in expected):
                raise ValueError("Stored case differs from the benchmark fixture. Use a clean database and import the bundled JSON.")
            if not participant.strip():
                raise ValueError("Enter a participant/session pseudonym")
            st.session_state["triage_benchmark_active"] = {
                "participant": participant.strip(), "case_id": case["case_id"], "workflow": workflow,
                "case_set_sha256": fingerprint, "group_id": group_id, "started": time.perf_counter(),
                "baseline_reviewed_at": get_investigation(group_id)["updated_at"],
                "baseline_ai_id": max((item["id"] for item in list_drafts(group_id)), default=0),
            }
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    active = st.session_state.get("triage_benchmark_active")
    if active:
        st.info(f"Active trial: {active['participant']} / {active['case_id']} / {active['workflow']}. "
                "Open Alert triage, work this case, save your reviewed record, then return here.")
        with st.expander("Scoring rubric for the active case (score the initial draft)"):
            st.json(next(item for item in cases if item["case_id"] == active["case_id"]))
        if "elapsed_seconds" not in active:
            if st.button("Stop timer after reviewed record"):
                record = get_investigation(active["group_id"])
                drafts = list_drafts(active["group_id"])
                if not record["reviewed"] or record["updated_at"] == active["baseline_reviewed_at"]:
                    st.error("Save a new analyst-reviewed record during this trial before stopping.")
                elif active["workflow"] == "ai-assisted" and not any(
                    item["status"] == "valid" and item["id"] > active["baseline_ai_id"] for item in drafts
                ):
                    st.error("The AI-assisted workflow requires a valid AI draft requested during this trial. Failed attempts can be documented in the trial notes.")
                else:
                    active["elapsed_seconds"] = time.perf_counter() - active["started"]
                    st.rerun()
        else:
            st.metric("Time for case (seconds)", round(active["elapsed_seconds"], 2))
            st.write("Score the initial analyst draft (manual) or model draft (AI-assisted), before corrections. "
                     "Count rubric items missed and individual unsupported factual claims; do not count questions as claims.")
            with st.form("benchmark_score"):
                missed = st.number_input("Evidence items missed", min_value=0, max_value=4, value=None, step=1)
                unsupported = st.number_input("Unsupported claims", min_value=0, value=None, step=1)
                mistake = st.text_area("AI mistake (blank if none)")
                correction = st.text_area("Analyst correction (required when recording an AI mistake)")
                submitted = st.form_submit_button("Save benchmark result")
            if submitted:
                try:
                    save_run({**active, "evidence_missed": missed, "unsupported_claims": unsupported,
                              "ai_mistake": mistake, "analyst_correction": correction})
                    del st.session_state["triage_benchmark_active"]
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        if st.button("Discard this timer (saved investigations are retained)"):
            del st.session_state["triage_benchmark_active"]
            st.rerun()
    render_results()


def render_results() -> None:
    rows = list_runs()
    st.subheader("Recorded benchmark results")
    if rows:
        st.dataframe(rows, hide_index=True)
        try:
            st.json(summarize(rows))
        except ValueError as exc:
            st.error(str(exc))
    else:
        st.info("No results entered yet. Record both workflows for the same participant and case to calculate paired medians.")
    st.download_button("Download benchmark CSV", export_csv(rows), file_name="triage-benchmark.csv", mime="text/csv")
