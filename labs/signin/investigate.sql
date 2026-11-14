-- SYNTHETIC fixtures only. Keep the lookalike and duplicate for comparison.
-- The source timestamp strings explicitly include UTC offsets.
SELECT event_id, timestamp, source, event_type, severity, "user", host, evidence
FROM events
WHERE event_type = 'sign_in'
  AND "user" = 'alex@example.test'
ORDER BY timestamp, event_id;
