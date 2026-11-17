# 共通受け皿：独立検証概要（EVP/1 20261117-020）

**Status:** VERIFIED (tested commit and observed Linux/root behavior only)  
**Date:** 2026-11-17 (JST)  
**Tested commit:** `d9b24aa2c75fb022eb7f58fb04e94ccbc33ab3a9`  
**Verdict:** E.L.I.S. ACCEPT_WITH_CONDITIONS / PILOT → VERIFIED.

**Evidence provenance:** This page records **V.E.S.T.A.R.D.'s reported measurements** from a fresh clone, not a claim that E.L.I.S. directly ran the tester's commands. The tester's full private execution log and complete fresh-Muse explanation were not transferred for source-by-source independent inspection. No private paths, data or logs are reproduced.

## Reported results

| Criterion | Measured/reported result |
| --- | --- |
| Fresh clone | HEAD = `d9b24aa` |
| Entire test suite | **116/116 PASS** (previous 67 + shared-intake 49); the interim development count of 41 was not the final test count |
| Deterministic item_id | From `source_id` and `source_event_id`; flag shows 1 unprocessed item |
| Duplicate ingest | `added=false`; authoritative journal still has only one event line |
| Invalid state transition | Direct `unprocessed → reported` rejected; exit 1 |
| Valid transitions | `unprocessed → audited → reported` succeed |
| Missing `when_fetched` | Rejected; exit 1 |
| Modified derived flag | `status` warns `flag.json:stale`, reports correct count reconstructed from journal; `rebuild` repairs derived data |
| Corrupted authoritative JSONL | `Corrupted journal JSON`, exit 1, fail closed |
| Acquisition failure | `run-start → run-error(FETCH_TIMEOUT) → run-finish(outcome=error)` recorded as `COMPLETED + error`; not misreported as zero new items |
| Retention preview | 90-day candidate selection; `deleted=false`; `unprocessed` and `audited` never eligible |
| Untagged adapter | Pending `event_id` retained as `source_event_id`; no automatic source-side ack |
| Fresh Muse explanation | Reporter assessed PASS: no semantic decisions by receiver, append-only source of truth, no deletion of unprocessed, 90-day preview only, acquisition error not equal to 0, and ack-order dangers |

## UNVERIFIED limitations

- **Platform and permission scope:** the tester's environment was Linux with root privileges. Non-root access errors, Windows, NFS and other network filesystems were not independently validated.
- Cross-file atomicity is **not** claimed. Each event append and derived-file update is separately durable; the recovery strategy relies on retry with the same item identity and rebuild of derived outputs.
- Large historical journals, performance and prolonged operation were not measured by this report.
- The clean-room Muse explanation was assessed and saved privately by the tester; its full text was not supplied for direct review.
- The kit's overall status remains **PREVIEW**, not formally RELEASED. This VERIFIED designation does not extend to changed code, private production integrations, automated delivery or deletion.

## Follow-up gate

Before any formal P5 release, verify release files with an appropriate SHA-256 manifest and anchor checks, run non-root permission-denial scenarios, independently assess platform-specific locking on supported platforms, and confirm the owner's explicit approval. Never put actual paths, real records, credentials, or sensitive logs into the public repository.
