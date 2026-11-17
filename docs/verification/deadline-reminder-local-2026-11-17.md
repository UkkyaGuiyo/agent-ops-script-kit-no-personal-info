# 第7号 期限リマインダー係：制作側ローカル検証

**Date:** 2026-11-17 (JST)  
**Status:** PILOT; independent fresh clone and C-7 Muse explanation are PENDING.  
**Environment:** Linux container, root, Python 3.13.5 (local synthetic temporary directories, no user records or external network).

## Test commands and counts

- `python -m unittest discover -s tests -q` in this **isolated new-operator build directory**: **80/80 PASS**.
- `python -m py_compile scripts/deadline_reminder.py`: PASS.
- The previously verified public kit had **223** test cases. Whole repository combined testing **223+80=303 EXPECTED, NOT YET RUN/VERIFIED**. The independent tester must clone the exact new commit and run the entire suite.

## Synthetic CLI anchor checks

- First `register`: `added=true`; exactly identical retry: `added=false`.
- `check --at-utc 2026-11-17T01:59:59+00:00`: `new_fired_count=0`.
- `check --at-utc 2026-11-17T02:00:00+00:00`: `new_fired_count=1`, `pending_delivery_count=1`.
- One second later: `new_fired_count=0`, pending remains **1**.
- All checks report `delivery_attempts=0`, `external_delivery=NONE`.
- Synthetic `ack`: `consumer_verified=false`; local attested delivery count becomes **1**. This is **not** independent evidence that any external consumer accepted a real item.
- After registration, firing, and this synthetic acknowledgment, the append-only journal has **3** event lines. Source sample SHA-256 unchanged.

## Explicit security and edge tests

- Three-way UTC/IANA/epoch cross-check; invalid UTC offset, epoch boolean/float/string, timezone mismatch, nonexistent DST local hour, repeated JSON keys, NaN and unknown schema rejected.
- Single fire at deadline equality; no duplicate firing; stable pending outbox identifier; cancellation history; rescheduling replaces one active ID with a new active ID without deleting the previous record.
- Journal corruption, partial line, wrong version, sequence gap fail closed. Derived outbox missing or stale can be reconstructed without altering journal.
- A simulated exception after a durable fire journal append and before derived outbox write is repaired by the next check; no new fire is generated on recovery.
- Separate failure state survives unreadable journal, records a single open error episode while recurring, closes on successful check, and records a distinct new episode upon later recurrence. Its hash is a consistency digest, not cryptographic authentication.
- Local lock collision, symlinked state/journal, unknown CLI commands rejected. Source input remains unchanged.
- No actual network transport, scheduler, cron installation or downstream shared-intake write was exercised or exists in the public pilot.

## Limits and remaining gate

- Live non-root permission-denied filesystem behavior, Windows/macOS, missing IANA tzdb, NFS, large datasets, long-term history and external consumer attestation authenticity were not independently validated.
- The manual `ack` is **an untrusted witness statement** supplied as JSON, not verifiable proof of consumer presence. Do not use its `delivery_state=delivered` to claim true external delivery.
- All synthetic files must be screened before public commit. Keep runtime journals, outbox, failure state and actual user IDs outside the public repository.
- Reproduce fresh-clone 303/303 expected tests, exact CLI anchors, recovery after injected failure, C-7 initial-Muse explanation, and code/blob hash manifest check. Only then consider revision-scoped VERIFIED. P4 security/release audit and explicit owner P5 approval remain separate.
