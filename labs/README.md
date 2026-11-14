# Hands-on investigation → reviewed ticket

**Current status:** the synthetic sign-in query was executed with coding assistance, its three results were imported into two Patchwise groups, and the analyst reviewed the case. Disposition: **Inconclusive**. Escalation: **Deferred pending follow-up evidence**. See the [reviewed draft sample](../docs/examples/signin-jira-reviewed.md). Authentication details, policy outcomes, subsequent session activity and Alex's confirmation remain pending. Tool: local DuckDB SQL log analysis, not a SIEM or Defender XDR. No AI-provider draft, benchmark measurements or network root cause is claimed. The steps below support reproduction; use a new output directory if `exports/signin-run-01` already exists.

## 1. Run and preserve the query yourself

From the Patchwise repo root:

```bash
. .venv/bin/activate
pip install -r requirements-lab.txt
python -m labs.signin.run_query --output exports/signin-run-01
```

DuckDB runs `labs/signin/investigate.sql` against the existing synthetic fixture, retaining both duplicate observations and the lookalike for the same user. The script produces `events.json`, `events.csv`, `query.sql`, and `manifest.json`. It records tool/version, UTC execution time, source/query/export hashes and original event IDs. Choose a new output directory for each run; earlier evidence is never overwritten. This small query/export helper avoids a separate adapter: its JSON and CSV already match Patchwise's input contract. It never imports automatically, calls AI, or assigns a disposition.

Read the exact returned events. Use these prompts, recording your own conclusions in `signin/investigation.md`:

- What do the outcome, MFA and device-known fields establish? What do they leave unproven?
- How does the lookalike differ? Is the fixture's VPN approval message independent corroboration?
- Are the duplicate observations independent evidence?
- What event ID and field changed your interpretation, if any? If none changed it, record that honestly.
- What evidence would you seek before escalation (e.g. independent user confirmation or device context)?

Capture the terminal output, actual query and hashes. Do not describe the synthetic fixture's assertions as verified real-world facts.

## 2. Import those same results into Patchwise

Open the existing app at `http://127.0.0.1:8501`, or launch `streamlit run app.py` in another activated terminal. In **Alert triage**, upload `exports/signin-run-01/events.json` (CSV is equivalent), then click Import events. Compare all imported IDs and UTC timestamps against the query export. Record the displayed counts. If the original fixture was already imported, identical rows are reported already present; that is expected idempotency, not a new investigation result.

The export should contain three rows, grouped as one duplicate group and one separate lookalike group. This is an expected fixture check, not a result of your investigation. Patchwise reviews one group at a time: review both groups, and explicitly reference the lookalike ID in the context notes of the suspicious group. It is not included in that group's AI payload or timeline; retain the complete query export with the ticket artifacts. Do not imply that the AI saw the comparison event when it did not.

Save an unreviewed analyst record with your timeline, supporting IDs, evidence, uncertainties and tentative assessment. Preserve an initial JSON export if you want a before/after record.

## 3. Request AI help, then verify each claim

The implementation check found no locally configured key. Set `PATCHWISE_AI_API_KEY` in your ignored `.env` yourself; never paste the key into chat or a lab write-up. The existing `.env.example` documents model/endpoint configuration. If AI is unavailable, continue manually and leave AI-assisted deliverables/trials pending.

In Alert triage, select the suspicious group's events, inspect the exact minimized payload, approve it, and request a draft. The existing safeguards validate schema and selected ID membership and preserve the investigation on failure. The new comparison view places each saved valid draft claim next to its cited full normalized local event, including evidence omitted from the AI payload. The complete original query export remains your primary comparison artifact.

For each factual claim, copy its attempt number, text, IDs, supporting source fields and your supported/unsupported/uncertain verdict into `signin/claim-review.csv`. If unsupported or overconfident, record the actual correction in that file and your analyst record. Inspect missing-evidence flags too. If no correction is observed, say so; do not invent a model mistake. Export the saved AI history.

Only after verifying every claim, choose the disposition and escalation rationale yourself, check the analyst review box, and save. Download the reviewed investigation JSON and Jira Markdown. No external ticket is created. Keep the comparison event in an accompanying reviewed record/JSON and attach the full query export when assembling the final ticket package.

## 4. Run four paired benchmark cases yourself

Use **the original six-event fixture** `examples/identity-network-events.json` for benchmarking, not just the three-row query export. Follow the existing `docs/benchmark.md` rubric and app timer. `benchmark-order.csv` gives eight trials with first workflow alternating by case. This is a schedule, not a result file.

Keep two clean app databases, one per workflow, to hide previous notes. For example, use separate terminals/ports:

```bash
PATCHWISE_DB_PATH=.patchwise/bench-manual.db streamlit run app.py --server.port 8502
```

```bash
PATCHWISE_DB_PATH=.patchwise/bench-assisted.db streamlit run app.py --server.port 8503
```

Import the original fixture into each, use the same participant/session pseudonym, and follow the schedule across the two apps. For every trial: start timer before reading evidence; preserve and score the initial draft; correct it; save a new reviewed record; stop timer; enter actual scores and save. Assisted trials require a valid AI draft produced during that trial. Do not turn a failed AI request into an invented successful trial. Keep failure/exclusion notes.

Export both app CSVs. Combine their rows under one header into `exports/triage-benchmark.csv` without duplicating rows. Run:

```bash
python -m patchwise.core.benchmark --csv exports/triage-benchmark.csv > exports/benchmark-summary.json
```

`benchmark-results-pending.csv` contains only the result schema. Actual completed sample size is currently **0 pairs**. Planned size: four pairs / eight trials / one participant. Report completed pairs and excluded/incomplete cases from the actual summary. Limitations include a tiny synthetic sample, one analyst, prior familiarity with these fixtures, residual practice effects despite alternating order, subjective rubric scoring and provider/network variation. Report time and quality together; do not generalize performance to a SOC.

## 5. Separate network case: DNS in an isolated sandbox

Use `network/write-up.md`, copied from the existing network template. This remains a separate lab write-up; it is not imported into alert triage. Wireshark/Packet Tracer availability is awaiting analyst confirmation.

A reproducible Packet Tracer topology is a client `192.0.2.10/24`, DNS server `192.0.2.53/24`, HTTP server `192.0.2.20/24` and a switch, all inside the simulator. Enable HTTP on the web server; create an `app.lab.test` A record pointing to it; set the client resolver to the DNS server. Establish a working baseline by visiting the IP and hostname. Save the topology before introducing a fault.

Have a lab partner introduce one DNS fault (or deliberately configure one and disclose that in the report). Diagnose using client configuration, DNS records/service, IP-versus-hostname access and DNS/HTTP events in Simulation mode. Record observations before deciding the root cause. Apply the fix you identify and repeat the original failing hostname test plus the IP baseline. Save before/after topology files and simulation screenshots.

If using Wireshark instead, use an isolated VM/sandbox DNS and web server with the same topology. Capture the lab interface while running `dig @<DNS_IP> app.lab.test A +time=2 +tries=1` and checking the lab web server by IP. Filter `dns`, inspect query/response IDs, requested name, server address, answer and response code; `dns.flags.rcode != 0` isolates DNS error responses. A timeout alone does not establish why resolution failed. Record routing/firewall/resolver checks as needed. Repeat the same query and application test after your fix. Save actual before/after captures; never fabricate packets or verification.

## Deliverables to finish after execution

- `exports/signin-run-01/`: actual query export and provenance manifest.
- Completed `signin/investigation.md` and `signin/claim-review.csv`.
- `exports/signin-ai-history.json`, `exports/signin-reviewed.json`, `exports/signin-jira.md`: real model/review exports (pending).
- `exports/signin-lookalike-reviewed.json`: comparison record; preserve its underlying ID with the full source export.
- `exports/triage-benchmark.csv` and `exports/benchmark-summary.json`: measured paired results (pending).
- Completed `network/write-up.md` plus actual `.pkt` or `.pcapng` and before/after screenshots (pending).

## References

- [DuckDB Python JSON ingestion](https://duckdb.org/docs/1.4/clients/python/data_ingestion): local JSON query support.
- [Wireshark DNS fields](https://www.wireshark.org/docs/dfref/d/dns.html): query, response and response-code inspection.
- [Azure Data Explorer public KQL help cluster](https://learn.microsoft.com/en-us/azure/data-explorer/web-ui-samples-query): an optional future KQL exercise using a Microsoft sign-in and no Azure subscription; ADX is an analytics tool, not a substitute claim of SIEM use.
