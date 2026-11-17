# 第9号 P1調査：Notion案件収集係 / Notion Jobs Collector

**Status: PLANNED.** This authorizes generalized **P1 source inventory only**, not implementation, account connection, web access, Notion changes, job ingestion, scheduling or formal release.  
**Basis:** E.L.I.S. EVP/1 `20261117-037` selected the next P1 after eight scoped VERIFIED operators. The existing P0 catalog's only grounded public goal is **"Synthetic job intake examples"**. Do not assume live Notion connectivity or private implementation maturity from the name.

## Why this next
A synthetic normalization and local preview workflow can be investigated without granting external-account credentials or modifying records. This order does **not** grant permission to read, edit or create real Notion pages, tasks, diaries, project memories, or jobs. It is lower-risk than authorizing retention deletion; Gmail and the separate Retention manager remain future independent scopes.

## V.E.S.T.A.R.D. P1 questions

1. **Real identity and status:** What is the confirmed private purpose, actual source(s), authoritative internal design/version and evidence of implemented versus planned behavior? Does "Notion jobs collector" mean jobs **from Notion**, jobs **to Notion**, or a different internal workflow? Do not guess.
2. **Collection scope:** Precisely which user-approved databases/pages or record categories are contemplated, and which are excluded? Explain only **generalized types**, not actual names, URLs, page IDs, content or private schema copies.
3. **Access and trust:** How are permission scopes, auth, rate limits, access revocation, page properties, shared/private workspace boundaries and data provenance handled? Does the internal tool have read-only capabilities, writes, or none? Distinguish implemented and proposed.
4. **Item identity and typing:** What minimal fields establish job/task identity and reproducible deduplication? Define fields (synthetic `source_id`, `source_event_id`, title alias, due timestamp/timezone if relevant, state and source revision) and mark actual/UNKNOWN; do not invent mandatory fields absent from the confirmed private design.
5. **Selection and change detection:** How does it distinguish new/changed/removed entries and avoid false "no jobs" claims? Which timestamps, pagination cursors, database query filters, incremental checkpoints and stable identifiers are actually supported?
6. **Output and local integration:** What data is prepared for Shared Intake v1 and with what privacy-minimizing transform? Does any confirmed workflow call Shared Intake or only produce a local JSON draft? No real inbox/outbox delivery is authorized for the first public pilot.
7. **State, replay and acknowledgment:** Source fetch versus durable acceptance versus human action, duplicate/collision handling, failed ingestion retries, pending queues, ack and any separate ledger; state NONE if no implementation.
8. **Failures and recovery:** Unauthorized account, revoked token, unavailable page/database, schema change, partial page results, invalid timestamps, malformed property, pagination failure, corrupted state, read limits. Such failures must be **ERROR/UNKNOWN**, not "0 jobs."
9. **Privacy/retention authority:** Are real task names, client identifiers, attachments, URLs, dates and text necessary? What exact redaction, local retention and publication boundaries apply? Confirm there is **no public export of personal data**, no unsolicited change to existing Notion pages, AI board, task directions or diaries.
10. **Synthetic tests and fresh-Muse C-7:** Empty complete source versus fetch error, duplicate job ID, missing required field, revision conflict, malformed timestamp, pagination truncation, stale snapshot, private field exclusion, retry without duplicate, stable mapping to Shared Intake v1 if approved. Explain source fact vs AI interpretation vs human approval, **"収集・候補化は応募・登録・完了ではない"**, and no live Notion account action.

## Requested P1 report

- Clearly separate **FACT (tested private behavior)**, **approved design**, **UNKNOWN**, **UNVERIFIED**, and proposed public choices.
- Generalized input/output schemas and timestamps with units/timezones, stable IDs, state and error codes.
- Minimal-access permission and authority matrix: inspection, transformation, local preview, private intake, Notion write, external outreach.
- Identity/duplicate/retry contract; source completeness proof and Fail Closed contract.
- Synthetic test matrix, C-7 criteria, and unresolved U1...Un.
- If the internal tool is absent, explicitly report its absence and present only verified design/manual steps.

## Boundaries

No private Notion names, page IDs, actual URLs, real task descriptions, screenshots, account data, login tokens, real logs or client information. Do not connect to Notion, read/write pages, create databases, change existing AI bulletin boards, task instructions, diaries or memories as part of P1. Do not create or modify schedules, send messages, ingest real jobs, or edit public/private source code on P1. Public implementation requires a new separately reviewed design and synthetic pilot. Full kit remains PREVIEW; P4/P5 release audits/approval are independent.
