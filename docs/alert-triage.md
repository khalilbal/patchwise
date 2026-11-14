# Event intake and analyst review

Use synthetic or authorized lab data. All intake, analyst notes, AI attempts and benchmark records use the existing SQLAlchemy/SQLite database. The five new tables are created with `Base.metadata.create_all`; existing scanner tables and finding priorities are unchanged. Back up an existing database before upgrading. No external tickets or escalations are created.

## Input contract

Upload a UTF-8 JSON array of objects, or CSV with a header and one event per row (2 MiB / 5,000 events maximum). Fields:

| Field | Normalization |
| --- | --- |
| `event_id` | Trimmed original ID, maximum 255 characters, globally unique across sources. If absent, `generated-` plus SHA-256 of the normalized content before the ID and gap list are added. |
| `timestamp` | ISO 8601 with `Z` or explicit offset; converted to UTC. Missing, invalid or timezone-naive values become null with a gap. Never substitute import time. |
| `source`, `event_type` | Trimmed, lowercase, default `unknown` with a gap. |
| `severity` | Lowercase critical/high/medium/low/info/unknown; unsupported values become unknown with a gap. |
| `user`, `host` | Trimmed, case preserved. At least one is needed for complete evidence. |
| `evidence` | JSON object. In CSV, put a JSON object in the quoted cell. Free text becomes a `message` field. Empty/missing/all-empty evidence is flagged. |

Other columns and the original row stay local in `alert_events.raw_json`; normalized evidence is available in investigation JSON. Structural errors reject the batch. Scalar fields are limited to 255 characters. Missing data does not reject an otherwise valid event. See the included JSON and equivalent CSV fixtures.

## Deterministic grouping: exact-evidence-v1

For a complete event, the group key is SHA-256 over compact sorted-key JSON of:

```
["exact-evidence-v1", floor(UTC_unix_seconds / 300),
 source, event_type, severity, user, host, evidence]
```

Original event ID and exact timestamp are excluded from the key. All evidence keys and values must match exactly; evidence key order does not matter. Bucket windows are fixed UTC intervals (e.g. 09:00:00–09:04:59.999999), not sliding windows. Events across a bucket boundary remain separate even if close in time. Different outcomes, MFA signals, source IPs or message text remain separate. This conservative rule groups duplicate observations; it does not correlate an attack campaign or establish maliciousness. Event counts represent observations, not independent incidents.

Any normalization gap makes the key SHA-256 over `["exact-evidence-v1", "incomplete", event_id]`. Two incomplete events with different IDs never merge. Reimporting the same ID and normalized content does nothing. Reusing an ID with different normalized content rejects and rolls back the whole import, including new events earlier in that batch. Use source-prefixed IDs upstream if different sources reuse identifiers. A group keeps every underlying original ID. New evidence added to a previously reviewed group clears its review flag.

The fixture has six events and four groups: suspicious sign-in with a duplicate, a separate benign lookalike, a network connection with a duplicate, and an event with no evidence. Labels describe synthetic scenarios, not verified real-world findings.

## Review and export

1. Open **Alert triage**, import the fixture, and select a group.
2. Inspect UTC event times and evidence, including explicit intake gaps.
3. Write a summary and timeline notes. Select supporting event IDs and cite IDs in factual prose. Record supporting evidence, missing context/follow-up questions, disposition and the reason to escalate or not escalate. Use `None identified` if no additional gap was found; do not leave it blank to imply completeness.
4. Save while investigating. When ready, check the analyst review box and save again. A reviewed record requires summary, supporting evidence, at least one valid event ID, missing context and escalation rationale.
5. Download the investigation JSON at any stage. Download the reviewed Jira Markdown draft when review is complete. It includes the full timeline, available evidence, all original IDs, disposition and escalation rationale. Paste it into a ticket only after your own decision to do so.
6. **Reports** also exports all alert investigations and AI history, even when no scanner projects exist. Existing project Markdown/JSON reports remain available.

Manual prose is not semantically fact-checked. Selecting an ID does not prove the associated assertion. Exports are last-saved records; save edits before downloading.

## Optional AI

Set the existing `PATCHWISE_AI_API_KEY`, `PATCHWISE_AI_MODEL` and optional `PATCHWISE_AI_BASE_URL` in a local `.env`. The provider must implement the existing Chat Completions-style endpoint and accept the configured model's `temperature` and `max_tokens` parameters. The base URL must use HTTPS with no embedded credentials, query or fragment. Redirects are disabled. No extra SDK is required.

Select events, inspect the exact payload preview, explicitly approve it, and click **Request AI draft**. Only IDs, UTC time, severity, intake gaps and validated allowlisted signals are sent: IP addresses, boolean MFA/device-known, enumerated outcome/protocol, integer destination port and a two-letter country code. User/host/source/type strings, raw messages, arbitrary evidence, analyst notes and repository source are omitted. Omitted fields are counted. Review IDs and IPs in the preview because these can still identify sensitive activity. Missing fields may limit the draft's usefulness; inspect the complete local evidence yourself.

The system prompt treats all event content as untrusted data, prohibits instructions inside events and requests cited factual claims, follow-up questions and missing-evidence flags. The request has no tools. A strict local validator rejects bad JSON/schema, empty citations, IDs outside the selected events, and absent gap flags when evidence was missing or omitted. Valid ID membership is **not semantic grounding**: an invented assertion can cite a real ID. An analyst must verify every claim and correct or reject it.

AI attempts are stored separately from analyst records. Errors use fixed messages, not provider response bodies or exception details that might expose credentials. A request failure or rejected draft leaves the investigation intact and allows retry/manual export. AI history exports include valid outputs and safe failure messages; rejected raw output is intentionally not retained. To document an invalid-response mistake, record its description and your correction in benchmark notes. No key is needed for import, review, disposition, JSON or Jira export.
