# Portfolio collection checklist

Create a local `exports/` folder; it and local `.patchwise/` databases are ignored. Review all artifacts before publishing. Use synthetic fixture data for application screenshots. No actual benchmark results or SIEM/network findings are included in this repository.

Collect these exact files (rename downloads to distinguish workflow and case):

- `exports/pytest.txt`: terminal output of `python -m pytest -q`, with date and environment recorded separately.
- `examples/identity-network-events.json`, `examples/identity-network-events.csv`, `examples/benchmark-cases.json`: inputs and scoring rubric; keep their dataset fingerprint with results.
- `exports/alert-triage-report.json`: Reports → Download alert triage report, containing traceable normalized events, saved records and AI draft/error history.
- `exports/manual-<case>-initial.json`: investigation JSON exported before corrections in each manual trial.
- `exports/assisted-<case>-ai-drafts.json`: saved AI history including the actual draft evaluated and any safe failure messages.
- `exports/<workflow>-<case>-reviewed.json` and `exports/<workflow>-<case>-jira.md`: corrected investigation and reviewed Jira draft, for each workflow/case.
- `exports/triage-benchmark.csv`: merged measured results with one header; `exports/benchmark-summary.json`: `python -m patchwise.core.benchmark --csv exports/triage-benchmark.csv > exports/benchmark-summary.json` after both workflows are complete.
- Completed copies of `docs/labs/siem-investigations.md` and `docs/labs/network-troubleshooting.md`, plus query text, sanitized key-event exports, network command outputs and before/after captures referenced in those write-ups.

Capture these screenshots after performing the workflow:

1. `exports/01-import-groups.png`: successful six-event import and four-group table; the suspicious and benign lookalike groups are visibly separate.
2. `exports/02-duplicate-timeline.png`: selected duplicate sign-in group showing both original IDs, UTC timeline and evidence.
3. `exports/03-missing-evidence.png`: incomplete case with explicit missing-context warning.
4. `exports/04-reviewed-draft.png`: saved summary, supporting IDs, disposition, escalation rationale and enabled Jira draft download.
5. `exports/05-ai-payload-and-review.png`: selected-event payload preview plus an actual cited model draft. Do not expose credentials or unapproved identifiers.
6. `exports/06-ai-error-preserved-record.png`: an actual safely induced request/validation error alongside the preserved saved investigation. Mocked automated-test evidence should be labeled as simulated.
7. `exports/07-benchmark.png`: your completed paired trials, entered quality scores and measured summary after running them.
8. `exports/siem-01-query-events.png`, `siem-02-query-events.png`, `siem-03-query-events.png`: actual SIEM queries, UTC range and key events that support your dispositions.
9. `exports/network-topology.png` and `exports/network-before-after.png`: sandbox topology and observed verification of your fix.

Clearly label synthetic application cases, mocked automated checks, and hands-on lab observations. Only report work and measurements you actually performed.
