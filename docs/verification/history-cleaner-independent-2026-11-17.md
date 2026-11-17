# 第8号 履歴掃除係：独立検証概要（EVP/1 20261117-037）

**Date:** 2026-11-17 (JST)  
**Tested code commit:** `61c3364af28a5f367205f4d8c41d587e9ce9e97f`  
**Verdict:** E.L.I.S. `ACCEPT_WITH_CONDITIONS`, PILOT → VERIFIED **only within tested revision and Linux/root read-only scope**.  
**Source:** V.E.S.T.A.R.D. independent new-clone report; full tester logs and C-7 transcript are retained privately and were not supplied to or independently reproduced by E.L.I.S. E.L.I.S. reread the public technical specification, Python source and local test code for the stated revision. No real data or private paths are embedded here.

## Reported measurements

| Criterion | Observation | Status |
| --- | --- | --- |
| Clone identity | HEAD matches `61c3364af28a5f367205f4d8c41d587e9ce9e97f` | PASS (reported) |
| Combined test suite | **370/370 PASS**: previous 303 + history cleaner 67 | PASS (reported) |
| Public Shared Intake integration | Previously skipped producer-side integration was run successfully against the actual public Shared Intake CLI; **0 SKIP** in full suite and isolated run PASS | PASS (reported) |
| Synthetic source events | **8 event rows** | PASS (reported) |
| Item classifications | `candidate=2`, `excluded=2`, `hold=0` | PASS (reported) |
| Safety boundary | `safe_to_delete_count=0`, `records_changed=0`, `dry_run=true` | PASS (reported) |
| Exact 90-day equality | `7,776,000 seconds` since terminal transition: candidate, `cutoff_inclusive=true` | PASS (reported) |
| Active/unfinished items | `audited` and `unprocessed` → `NONTERMINAL_NEVER_PRUNE`, excluded | PASS (reported) |
| Reminder origin | Reminder-derived item can be age candidate but its **state events remain protected** | PASS (reported) |
| Delete authority | Every item has `deletion_safe=false` | PASS (reported) |
| Input integrity | All source file SHA-256 values identical before and after read-only CLI | PASS (reported) |
| Invalid JSONL | `status=error`, `INVALID_JSON`, exit 1, no classification counts (Fail Closed) | PASS (reported) |
| C-7 explanation | Five core requirements (Shared Intake records, nonterminal protection, candidate vs delete, protected error/seen/reminder/prune history, no actual delete feature) | PASS (reported) |
| Separated dedup memory and safe deletion | Not implemented | OUT_OF_SCOPE |
| Non-root, Windows/macOS, NFS and large live data | Not tested | UNVERIFIED |

## Decision boundary

This operator's "history" is **record history inside Shared Intake**, not Git history or files on disk. The 90-day threshold starts at the final terminal transition, not initial ingest. `candidate=2` means temporal eligibility for review, **never permission to remove two records**. The public Shared Intake v1 rebuilds deduplication identity from append-only `item_added` events; it does not currently supply independently durable `seen` memory, verified `prepare/complete` prune contracts, or post-prune replay safety. Therefore `safe_to_delete_count=0` remains mandatory. A SHA-256 match demonstrates byte identity, not a reliable right to delete.

**No authority granted:** no deletion of records or files, journal compaction, sequence renumbering, prepare/complete mutation, checkpoint writing, external services, schedulers or public tagged release. The public repository remains **PREVIEW**, requiring later P4 audit and separate P5 owner approval.
