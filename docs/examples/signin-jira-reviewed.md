# Jira ticket draft — analyst reviewed

> Portfolio sample from the actual analyst-reviewed export. All event identities, hosts, addresses and messages are synthetic lab data. The original local export remains unchanged. An earlier pending-decision note was omitted from this presentation copy; the final disposition, evidence and pending requests are preserved. “Intake gaps” below describes missing required import fields, not completion of the investigation.

No ticket has been created or escalated.

Group: 02dd76088dc638469535db4e9a9b6dfa27786645e07e20b568998611c115615e
Disposition: Inconclusive
Reviewed at (UTC): 2026-11-14T22:49:06.607251Z

## Summary
SYNTHETIC LAB — Inconclusive. signin-001 reports a successful sign-in for alex@example.test at 2026-10-01T09:01:00Z with mfa=false and device_known=false. These signals warrant investigation but do not establish compromise. signin-001-copy is a matching duplicate observation 20 seconds later, not independent confirmation of malicious activity.

## Timeline (UTC)
- 2026-10-01T09:01:00Z | signin-001 | identity-lab | sign_in | user=alex@example.test | host=lab-laptop-01
- 2026-10-01T09:01:20Z | signin-001-copy | identity-lab | sign_in | user=alex@example.test | host=lab-laptop-01
09:01:00Z signin-001; 09:01:20Z signin-001-copy. Comparison event signin-benign-002 at 09:02:00Z is in a separate group and the [synthetic source fixture](../../examples/identity-network-events.json): it reports mfa=true, device_known=true and source 192.0.2.10.

## Supporting evidence
signin-001 and signin-001-copy: outcome=success, mfa=false, device_known=false, src_ip=203.0.113.25. Exact matching evidence in the same five-minute bucket supports duplicate grouping, not two independent confirmations of maliciousness. The separate comparison event signin-benign-002 shows that the high severity label alone cannot distinguish these synthetic cases. Its VPN approval message is a fixture assertion, not independent corroboration.

Cited event IDs: signin-001, signin-001-copy

## Available event evidence
Event ID: signin-001
{"country":"ZZ","device_known":false,"message":"Unfamiliar sign-in. Lab signal only; validate travel and VPN context.","mfa":false,"outcome":"success","src_ip":"203.0.113.25"}
Intake gaps: None identified
Event ID: signin-001-copy
{"country":"ZZ","device_known":false,"message":"Unfamiliar sign-in. Lab signal only; validate travel and VPN context.","mfa":false,"outcome":"success","src_ip":"203.0.113.25"}
Intake gaps: None identified

## Missing context
PENDING — obtain authentication details for signin-001 to determine what mfa=false represents, including authentication methods and step outcomes.
PENDING — obtain the applicable authentication policy evaluation and enforcement outcomes.
PENDING — obtain subsequent session activity, correlated by session/request identifiers where available.
PENDING — after reviewing those records, ask Alex to confirm the sign-in with targeted context.
No requested authentication, policy, session or user-confirmation evidence has been supplied. Device-registration and independently verified VPN context also remain unavailable. The ZZ country placeholder cannot establish geography or impossible travel.

## Escalation rationale
Deferred pending follow-up evidence. The successful sign-in in signin-001, with mfa=false and device_known=false, warrants investigation. Request authentication details, policy outcomes and subsequent session activity first, then ask Alex to confirm the sign-in. Reassess escalation when that evidence is available. Neither compromise nor benignness is established; no external ticket or escalation has been initiated.

## Underlying event IDs
signin-001
signin-001-copy
