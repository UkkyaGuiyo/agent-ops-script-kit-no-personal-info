# 第7号 P1調査：期限リマインダー係 / Deadline Reminder

**Status: PLANNED; P1 inventory only.** No code, scheduling, alerts, sending, external-account action or formal release authorized.  
**Basis:** E.L.I.S. production-order decision for EVP/1 `20261117-028`, after six scope-limited VERIFIED operators. P0 catalog target is "Deadline notification and retry state"; this alone **does not establish actual internal behavior**.

## Why this operator next
It builds on the kit's distinction between observation, state, pending delivery and acknowledgment, and is a safer next independent pilot than implementing automatic file deletion. However, **the actual private reminder may work differently**. Obtain its generalized source-of-truth contract before public design. The public first pilot should favor **local preview without external sending, cron or recurring actions** unless a later separately authorized design says otherwise.

## V.E.S.T.A.R.D. P1 questions
1. **Purpose and observed maturity:** Does the private reminder actually run, or is it only a design? Which types of deadlines/reminders are in scope and which have measured evidence? Distinguish implemented, designed and UNKNOWN.
2. **Input and authoritative source:** What is a reminder item? IDs, source, label, due timestamp, timezone, completion/cancellation status, recipient, priority, lead time, evidence and content. Which fields are mandatory? Never disclose real tasks/recipients.
3. **Time semantics:** Exact deadline, local timezone and DST rules, early warning, grace window, on_time/overdue definitions, equality boundaries, clock drift and missed polls. State exact units (minutes, seconds, UTC timestamps).
4. **Trigger and recurrence:** One-shot versus repeating deadlines; a fixed reminder schedule or event-based scan; state what actually exists. Do not infer existing cron from previous discussions.
5. **State model:** Pending, eligible, fired, delivered, failed, acknowledged, canceled, completed as actually implemented (if any), with exact allowable transitions, terminal states and timestamp meaning.
6. **Duplicate/replay:** How can the same reminder avoid duplicate triggering across restarts? What is the idempotency key, event_id, lifetime, and behavior after partial failure or re-delivery? Distinguish trigger count from delivery attempts.
7. **Delivery boundary:** Does the private implementation write to a local inbox, call shared-intake, send notifications or use external providers? Exactly what constitutes durable acceptance and ack? What is the source of delivery truth? Report NONE/UNKNOWN where appropriate.
8. **Error/recovery:** Failed read, corrupt state, missed time window, notification failure, lock contention, interrupted save, invalid time/offset, unavailable destination, untrusted input. Never equate an error with "no reminders".
9. **Retention/security:** What historical records must remain, how long, and who can change deadlines or delete pending reminders? Protect recipient IDs, message text, schedule patterns, private account data and logs. Do not pass real examples.
10. **Synthetic tests and C-7 explanation:** Before/at/after due, time-zone variation, grace boundaries, restart replay, duplicate IDs, failed delivery and retry, source missing, corrupt state, never sending a real message during tests. Explain distinction between **"期限を検出"**, **"通知を渡した"**, and **"相手が読んだ"**.

## Deliverables
- Generalized P1 factual/design/UNKNOWN matrix with exact provenance;
- Typed input/output JSON schema, UTC/timezone and duration units;
- State-transition table, idempotency and retry/delivery contract;
- Authority matrix (read, preview, local queue, real send), explicit no-action boundary for the first public pilot;
- Failure/repair rules, synthetic test matrix and unresolved points U1...Un;
- Initial-Muse teaching criteria.

**Safety:** No private code, real reminders, exact addresses, actual paths, login IDs, logs, tokens or personal information. Do not change an existing private reminder, calendar, schedule, inbox, notification or GitHub repository during P1. No background automation or outbound delivery is authorized by this work order. Any public implementation must be independently designed, tested and audited after P1.
