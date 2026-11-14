# Patchwise

Patchwise is a local-first Python/Streamlit security workbench. It scans Python and Node.js projects with Bandit, pip-audit and npm audit, prioritizes vulnerability findings, and records investigations in SQLite through SQLAlchemy. A separate defensive alert workflow imports synthetic identity/network events, groups duplicates, supports analyst review and exports reviewed Jira-ready drafts. Ticket creation and escalation stay under human control.

## Sign-in investigation walkthrough

This synthetic case connects a **DuckDB SQL log-analysis lab** to a reviewed ticket draft. The query ran with coding assistance; the analyst reviewed the evidence and chose the disposition and escalation decision.

1. **Query:** The [actual SQL query](labs/signin/investigate.sql) selected three sign-in records for one synthetic user from the [source fixture](examples/identity-network-events.json), retaining the duplicate and lookalike for comparison.
2. **Investigate:** Patchwise grouped `signin-001` and `signin-001-copy` together and kept `signin-benign-002` separate. The successful sign-in with `mfa=false` and `device_known=false` warranted investigation; duplicate observations did not independently establish compromise.
3. **Review and export:** The analyst chose **Inconclusive** and **Deferred pending follow-up evidence**. The [reviewed Jira draft sample](docs/examples/signin-jira-reviewed.md) requests authentication details, policy outcomes and subsequent session activity, then Alex's confirmation. Those requests remain pending. No external ticket or escalation was created.

This demonstrates evidence traceability and an explained analyst decision using synthetic data. No AI-provider draft or benchmark improvement is claimed. See the [reproduction walkthrough](labs/README.md) for commands and limitations.

## Setup

```bash
git clone https://github.com/khalilbal/patchwise.git
cd patchwise
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Python 3.10+ is required (verified here with Python 3.13). npm/Node.js must be installed separately for npm audit. Dependency audits and vulnerability intelligence may need network access; event import, manual review and exports work offline. The default database is `.patchwise/patchwise.db`; an explicitly set `PATCHWISE_DB_PATH` overrides it. `.env.example` sets `patchwise.db` if copied unchanged. Back up an existing database before upgrading; the app adds alert tables without modifying scanner tables.

```bash
python -m pytest -q
# Optional, save the test output locally:
mkdir -p exports
python -m pytest -q > exports/pytest.txt
```

The scanner integration tests run real Bandit and fixture pip-audit responses, so they do not depend on a live package index. New triage tests use temporary databases and mocked AI responses; they require no credentials or live provider. Activate the virtualenv so the scanner executables are on `PATH`.

## Event import → reviewed ticket draft

1. Open **Alert triage** and import `examples/identity-network-events.json` (or its equivalent CSV). Six synthetic events produce four groups: a suspicious sign-in plus duplicate, a separate benign lookalike, a network connection plus duplicate, and a case missing evidence.
2. Select a group. Inspect original event IDs, UTC timeline, structured evidence and missing-context warnings. Grouping uses exact source/type/severity/user/host/evidence within a fixed five-minute UTC bucket. Incomplete events remain separate; identical reimports are idempotent. See [the input and grouping contract](docs/alert-triage.md) for boundaries, generated IDs and collision handling.
3. Enter an analyst summary, timeline notes, supporting event IDs/evidence, missing context, disposition and escalation rationale. Save your work. A suspicious signal is a reason to investigate, not proof of compromise.
4. Optionally use AI as described below. Verify any suggested claims against local evidence and put your corrections in the analyst record.
5. Check the analyst review box and save a complete record. Download **investigation JSON** and the **reviewed Jira draft**. The draft contains every underlying ID, evidence, timeline, disposition and escalation rationale. Save edits before exporting. You decide whether to paste the draft into Jira or escalate it; the app performs neither action.
6. **Reports** exports alert investigations/AI history independently of registered projects. Existing scanner project Markdown/JSON reports remain available. **Projects**, **Findings** and **Investigation** retain the scanner workflows and prioritization behavior.

## Optional AI drafts

Manual review and all exports work without an API key. To enable drafting, edit your local ignored `.env`:

```dotenv
PATCHWISE_AI_API_KEY=<your-local-key>
PATCHWISE_AI_BASE_URL=https://api.openai.com/v1
PATCHWISE_AI_MODEL=gpt-4o-mini
```

Use a compatible model/HTTPS provider endpoint. Never add real keys to tracked files. On Alert triage, save the investigation, select evidence IDs, inspect the exact minimized payload, approve sending it and request a draft. Raw log messages, user/host names, analyst notes and repository source are omitted. IDs/IPs can still be sensitive: inspect the preview. Logs are treated as untrusted input and the model has no tools or ticket actions.

Drafts require structured factual claims with selected event IDs, follow-up questions and explicit missing-evidence flags. Local checks reject unknown/unselected IDs and invalid responses. A valid citation can still support an incorrect claim; human verification is required. AI drafts and safe error messages are stored separately. A provider failure or rejected response preserves the analyst investigation. See [AI handling and limitations](docs/alert-triage.md#optional-ai).

## Benchmark and hands-on labs

Use **Triage benchmark** to time the same four cases manually and with AI, enter rubric scores and export your actual measurements. The dataset is fingerprinted; paired summaries exclude incomplete pairs. Start before reading the case, stop after saving the corrected reviewed record, and score the initial draft. No results are invented. Follow [the benchmark protocol](docs/benchmark.md), including its example of an unsupported model claim and analyst correction.

```bash
# After collecting and merging actual trial exports:
python -m patchwise.core.benchmark --csv exports/triage-benchmark.csv
```

The script reports manual/AI medians, `AI median - manual median`, percentage change, median paired change, and quality counts. Negative time changes indicate less time. Run both conditions before drawing conclusions.

Complete the blank templates after doing your own labs:

- [Three SIEM investigations](docs/labs/siem-investigations.md): SIEM, exact query, key event IDs/times, disposition and escalation rationale.
- [One sandbox network case](docs/labs/network-troubleshooting.md): topology, symptom, tool/commands, root cause, fix and verification.
- [Exact portfolio files and screenshots to collect](docs/portfolio-evidence.md).

Local databases, `.env`, and `exports/` are ignored. Sanitize artifacts before sharing. The app avoids mutating project files, installing dependencies or executing arbitrary project code during normal scans.

## Guided hands-on investigation

Follow [the local DuckDB-to-ticket walkthrough](labs/README.md) to reproduce the synthetic investigation and reviewed draft above, or prepare AI review, alternating benchmark trials and a separate DNS sandbox case. Install the optional lab dependency with `pip install -r requirements-lab.txt`. AI-provider review, benchmark measurements and network findings remain pending; DuckDB is labeled as SQL log analysis rather than a SIEM.
