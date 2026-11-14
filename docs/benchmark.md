# Paired manual and AI-assisted triage benchmark

No measurements or lab findings are supplied. `examples/benchmark-cases.json` is the scoring rubric, not a results file. The case-set SHA-256 covers the cases and the event fixture. The app checks imported case evidence against the fixture before starting a timer. Do not edit the fixtures between conditions.

## Protocol

1. Import `examples/identity-network-events.json` in Alert triage. Use a fresh database for each condition/session so prior notes and drafts are not visible. For example, launch once with `PATCHWISE_DB_PATH=.patchwise/manual.db streamlit run app.py` and later with `.patchwise/assisted.db`. Export results from each and combine their data rows under one CSV header. Use the **same pseudonym** in both databases to pair the same participant/session and case.
2. Run all four cases in both workflows. Counterbalance which workflow comes first (or alternate across participants), record the order separately, and keep machine, model, prompt version, dataset, network conditions and instructions constant. Familiarity with the cases can affect results; this small self-run exercise is descriptive, not a causal study.
3. On **Triage benchmark**, select the case/workflow, enter a participant/session pseudonym and click **Start case timer** before reading evidence. You can navigate to Alert triage and back without losing the timer while the Streamlit session remains connected. A server restart or lost browser session can lose an in-progress timer; discard and repeat that trial, do not invent elapsed time.
4. Manual condition: do not request/view AI drafts. Write an initial analyst draft from the events. AI condition: request an AI draft from the same case events. Include provider latency, retries, evidence review, corrections and the completed analyst record in the elapsed time.
5. Before correcting it, preserve the initial manual record or valid AI draft JSON and score it using the rubric below. Record scores on paper or locally so you can enter them after stopping. Then correct the draft, save an analyst-reviewed investigation, and return to Benchmark to **Stop timer after reviewed record**. The app requires a reviewed record and, for the assisted condition, a valid saved AI draft. Stop promptly; scoring/data entry after this point is outside the timer.
6. Enter scores, mistake notes/correction, and save. Export the initial draft, corrected investigation, reviewed Jira draft and result CSV. A participant/case/workflow may be saved once per session pseudonym. Never overwrite a bad result with a better retry; start a new trial and document why.
7. Combine both CSV exports, then run `python -m patchwise.core.benchmark --csv exports/triage-benchmark.csv`. Only complete manual/AI pairs sharing participant, case and dataset fingerprint enter the summary. Unpaired cases are reported and excluded; duplicate trials are rejected. The UI performs the same calculation on stored rows.

## Simple rubric

- **Evidence missed**: one point for each of the four `required_evidence` items absent or materially misrepresented in the initial draft, 0–4 per case. Count a bundled item once. Inspect underlying events, not only the AI preview, to score this.
- **Unsupported claims**: count each distinct factual assertion that cannot be established from the cited local evidence. An absent citation, invented ID, overclaim of compromise, or factual assertion attached to an irrelevant valid ID is unsupported. Questions explicitly framed as questions and cautious hypotheses are not factual claims. Record the claim text or a safe description with the correction.
- **Elapsed seconds**: from Start to Stop, including reading, initial drafting, in-task scoring, model requests, investigation review and corrections. Use identical boundaries in both conditions. Record interruptions/exclusions outside the results table.

For the assisted condition, quality scores describe the initial model draft; the final analyst record should reflect corrections. For manual, they describe the initial analyst draft. This compares initial-draft quality and end-to-end time; label those measures accordingly. Invalid AI responses are rejected before display and retained as safe errors. Document their effect on time and note the failure rather than treating a rejected response as a valid initial draft. If no valid draft is produced, record the failure separately; it is an incomplete assisted trial and should not be silently counted as a success.

## Calculations

For complete matched pairs:

```
manual_median = median(manual elapsed_seconds)
assisted_median = median(ai-assisted elapsed_seconds)
change_seconds = assisted_median - manual_median
change_percent = 100 * change_seconds / manual_median
paired_change = median(assisted time - manual time for each matched case)
```

Negative time changes mean less time in the assisted condition. The difference between medians and median of paired changes are different statistics; the script reports both. Sum evidence-missed and unsupported-claim counts separately for each condition. Report pair count and exclusions with the medians, and avoid claims of improvement before running the trials.

## Illustrative mistake record (not a benchmark result)

- Case: `suspicious-signin`
- Model assertion: “The account was compromised,” citing `signin-001`.
- Why unsupported: that event reports a successful sign-in without MFA on an unfamiliar device; it does not establish account ownership, travel or malicious intent. A real event ID can accompany a false claim.
- Analyst correction: “The successful sign-in needs investigation (`signin-001`, `signin-001-copy`). Confirm user activity, VPN/travel context and device registration before deciding whether to escalate.”
- Enter the assertion under **AI mistake** and the corrected statement under **Analyst correction**. Count the unsupported assertion under the rubric after inspecting the actual draft. Do not copy this illustration into a result row unless it actually occurred.

## Blank run notes

- Participant/session and workflow order:
- Date, machine, model, endpoint host (no credentials), prompt/code version:
- Dataset SHA-256:
- Interruptions, retries, failures and exclusions:
- Initial draft evidence artifact:
- Corrected record and Jira draft artifacts:
- Observed limitations:
