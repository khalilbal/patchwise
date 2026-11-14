from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from patchwise.ai.alert_drafting import DraftError, create_draft, list_drafts, minimized_events
from patchwise.core.config import load_config
from patchwise.core.alert_triage import (
    DISPOSITIONS, export_jira_draft, get_investigation, import_events,
    investigation_snapshot, list_alert_groups, parse_events, save_investigation,
)


def render_alerts() -> None:
    st.title("Alert triage")
    st.caption("Local synthetic identity/network events. Review and export drafts; ticket creation and escalation are manual.")
    st.write("Duplicates: exact source, type, severity, user, host and evidence in the same five-minute UTC bucket. "
             "Incomplete events remain separate. Original event IDs are retained.")
    uploaded = st.file_uploader("Import synthetic events (JSON or CSV, up to 2 MiB)", type=["json", "csv"])
    if st.button("Import events", disabled=uploaded is None):
        try:
            rows = parse_events(uploaded.getvalue(), Path(uploaded.name).suffix)
            result = import_events(rows)
            st.success(f"Added {result['added']} events; {result['already_present']} already present; {result['groups']} groups in this import.")
        except (ValueError, TypeError) as exc:
            st.error(str(exc))

    groups = list_alert_groups()
    if not groups:
        st.info("Import examples/identity-network-events.json or its CSV equivalent to begin.")
        return
    st.dataframe([{"group": group["group_id"][:12], "event_type": group["events"][0]["event_type"],
                   "severity": group["events"][0]["severity"], "events": len(group["events"]),
                   "disposition": group["disposition"], "reviewed": group["reviewed"]} for group in groups], hide_index=True)
    group_id = st.selectbox("Alert group", [group["group_id"] for group in groups],
                            format_func=lambda key: next(
                                f"{group['events'][0]['event_id']} — {len(group['events'])} event(s) — {group['disposition']}"
                                for group in groups if group["group_id"] == key))
    group = next(group for group in groups if group["group_id"] == group_id)
    events = group["events"]
    event_ids = [event["event_id"] for event in events]
    st.subheader("Event timeline and evidence")
    for event in events:
        st.text(f"{event['timestamp'] or 'UNKNOWN TIME'} | {event['event_id']} | {event['source']} | "
                f"{event['event_type']} | {event['severity']} | user={event['user'] or 'unknown'} | host={event['host'] or 'unknown'}")
        st.json(event["evidence"])
        if event["missing_context"]:
            st.warning("Missing context: " + ", ".join(event["missing_context"]))

    record = get_investigation(group_id)
    with st.form(f"investigation_{group_id}"):
        summary = st.text_area("Analyst summary", value=record["summary"])
        timeline_notes = st.text_area("Timeline notes (include UTC times and event IDs)", value=record["timeline_notes"])
        evidence_ids = st.multiselect("Supporting event IDs", event_ids, default=record["evidence_ids"])
        supporting = st.text_area("Supporting evidence (cite event IDs for factual claims)", value=record["supporting_evidence"])
        missing = st.text_area("Missing context / follow-up questions", value=record["missing_context"])
        disposition = st.selectbox("Disposition", DISPOSITIONS, index=DISPOSITIONS.index(record["disposition"]))
        rationale = st.text_area("Escalation rationale (include why escalation is or is not needed)", value=record["escalation_rationale"])
        reviewed = st.checkbox("I reviewed the evidence, claims, disposition and escalation rationale", value=record["reviewed"])
        saved = st.form_submit_button("Save investigation")
    if saved:
        try:
            save_investigation(group_id, {"summary": summary, "timeline_notes": timeline_notes,
                "evidence_ids": evidence_ids, "supporting_evidence": supporting, "missing_context": missing,
                "disposition": disposition, "escalation_rationale": rationale, "reviewed": reviewed})
            st.success("Investigation saved.")
        except ValueError as exc:
            st.error(str(exc))

    st.subheader("Saved record exports")
    st.caption("Downloads use the last saved record. Save edits before exporting.")
    snapshot = investigation_snapshot(group_id)
    st.download_button("Download investigation JSON", json.dumps(snapshot, indent=2),
                       file_name=f"investigation-{group_id[:12]}.json", mime="application/json")
    if snapshot["investigation"]["reviewed"]:
        st.download_button("Download reviewed Jira draft", export_jira_draft(group_id),
                           file_name=f"jira-draft-{group_id[:12]}.md", mime="text/markdown")
    else:
        st.info("Save a complete, analyst-reviewed record to enable the Jira draft export.")

    st.subheader("Optional AI drafting")
    st.caption("Save your investigation first. AI output is a separate draft; copy only claims you verify into your analyst record.")
    st.write("Citation checks verify ID membership, not factual accuracy. Review every claim against the local evidence.")
    selected = st.multiselect("Events to send for AI drafting", event_ids, key=f"ai_events_{group_id}")
    config = load_config()
    try:
        payload = minimized_events([event for event in events if event["event_id"] in selected])
    except DraftError as exc:
        st.error(str(exc))
        payload = []
    st.caption("Exact event payload preview. User/host names, raw logs and analyst notes are omitted. Event IDs and IPs may still be sensitive.")
    st.json(payload)
    consent = st.checkbox("I inspected the payload and approve sending these fields to my configured AI provider",
                          key=f"ai_consent_{group_id}")
    if not config.ai_api_key:
        st.info("No API key configured. All manual review and export features work without AI.")
    if st.button("Request AI draft", disabled=not (payload and consent and config.ai_api_key)):
        try:
            with st.spinner("Drafting from selected evidence…"):
                create_draft(group_id, selected, config)
            st.success("Draft saved separately. Verify its claims before using it.")
        except DraftError as exc:
            st.error(str(exc))
    drafts = list_drafts(group_id)
    if drafts:
        with st.expander("Saved AI drafts and errors", expanded=True):
            for draft in drafts:
                st.text(f"Attempt {draft['id']} | {draft['created_at']} | {draft['model']} | {draft['status']}")
                st.json(draft["result"])
                if draft["status"] == "valid":
                    by_id = {event["event_id"]: event for event in events}
                    for index, claim in enumerate(draft["result"].get("claims", []), 1):
                        left, right = st.columns(2)
                        with left:
                            st.text(f"Claim {index}: {claim['text']}")
                            st.caption("Verify support, uncertainty and omitted context before copying this claim into your analyst record.")
                        with right:
                            for event_id in claim["event_ids"]:
                                if event_id in by_id:
                                    st.json(by_id[event_id])
                                else:
                                    st.error(f"Cited event is unavailable: {event_id}")
        st.download_button("Download AI draft history", json.dumps(drafts, indent=2),
                           file_name=f"ai-drafts-{group_id[:12]}.json", mime="application/json")
