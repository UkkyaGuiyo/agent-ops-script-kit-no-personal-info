# 第4号 P1調査指示：共通受け皿（Shared Intake）

**STATUS: PLANNED — P1 generalization requested. No implementation or schedule authorized yet.**
**Basis:** E.L.I.S. next-production decision EVP/1 `20261117-018`.

## Rationale
The untagged watcher now provides a durable `pending` event but **no delivery service**. A receiver-side contract would support this pilot and future collectors, such as local Gmail/Notion examples, without assuming their credentials or real environments. Do not pretend the new receiver already exists.

## V.E.S.T.A.R.D. research questions (P1)
1. **Boundary:** What is the existing receiver's actual role and supported producers? Does it store, route, summarize, or deliver to an AI? Separate tested behavior from desired behavior.
2. **Envelope:** Document generalized field names/types for event ID, origin, time (time zone), event kind, payload, priority, source data, and optional evidence. Separate required and optional fields.
3. **Acknowledgment:** What is a durable accept? What does an acknowledgment mean, who/what sends it, and what must producers do after it?
4. **Idempotency:** Which identity key suppresses duplicates, for how long, and across restart/crash? What happens when the same ID has conflicting contents?
5. **States:** Define statuses for pending, accepted, delivered, delivery-failed/retry and already-consumed, strictly distinguishing UNKNOWN, false and NONE.
6. **Failure rules:** Storage write failure, malformed event, parse failure, absent input, receiver outage, partial batch, concurrency/locking, interrupted commit, stale lock and schema version mismatch. Retrieval failure ≠ zero events.
7. **Privacy/security:** Allowed synthetic payloads; disallowed personal names, paths, account/customer info, auth and logs; location and permissions of a private runtime queue; symlink/path escape rules.
8. **Retention/recovery:** Expected persistence, retry policy, deduplication, backup and safe recovery; distinguish recoverable staging from irreversible deletion. Never assume any existing cleanup agent may purge a pending report.
9. **Manual pilot:** Can a public example be a local CLI without network, external accounts, cron or AI runtime? What explicit proof would support its producer-side ack?
10. **Testing:** Synthetic accepted/rejected, replay/restart, duplicate and conflicting ID, crash at each state boundary, concurrent writers/readers, disk full, corruption, bounded memory and a new AI's beginner explanation.

## Deliverable
A **generalized** state-transition contract, typed JSON input/output schemas, error/exit codes, safe sample scenarios, actual-vs-unknown table, and unresolved design choices. Do not send private source, actual messages, credentials or local paths. No permission to change existing services, routes, or schedules. E.L.I.S. will review P1 before preparing independent public code.

## Preliminary safety rule
For the public pilot, prefer explicit local CLI input and a synthetic durable queue. **At-least-once producer retries require receiver-side deduplication**; a source-side stdout event must not be acknowledged as delivered merely because it was printed. These are design requirements, not claims that the internal implementation uses this exact contract.
