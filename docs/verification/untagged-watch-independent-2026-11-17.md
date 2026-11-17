# Untagged watcher / 独立検証概要

**Date:** 2026-11-17 (JST)
**Tested commit:** `dfb077beffcf97b3a3e983d64548daf04d12195d`
**Verdict:** ACCEPT_WITH_CONDITIONS, transition PILOT → VERIFIED for the tested scope.
**Exception:** live non-root filesystem permission-denial handling = **UNVERIFIED**.

**Source:** V.E.S.T.A.R.D.'s independent verification report EVP/1 `20261117-018`. This page records the independent tester's reported results; it is NOT a direct re-execution by the editor. The tester's private full logs and full clean-room Muse explanation are not published here.

## Reported observations

| Criterion | Tester-reported result |
|---|---|
| New clone | HEAD equals tested commit |
| Unit suite (whole project) | **67/67 PASS**: capacity 11 + ledger 23 + untagged 33 |
| First scan | `status=baseline`, new reports 0, exit 0 |
| Unchanged second scan | `status=ok`, new reports 0 |
| Newly created synthetic untagged file | `status=pending`, `event_id` issued, exit 0 |
| Scan while pending | same event ID and same report replayed |
| Ack of matching event ID | `status=acknowledged`; following scan `status=ok`, no reports |
| Tampered state with stale hash | `State integrity hash mismatch`, exit 1, no silent rebaseline; original state restored and resumed normally |
| Lock held by another process | `status=locked`, exit 3 |
| Monitored-root integrity | SHA-256 unchanged for pre-existing files; tester's synthetic additions excluded from the comparison |
| Fresh Muse beginner explanation | Reporter assessed PASS for baseline behavior, pending/ack, possible duplicate output, exit codes, state recovery risks, hash limitations, no personal data publication and lack of measured benefit guarantees |

## UNVERIFIED and boundaries

- **Live permission denial:** the tester ran as root, so a genuine inaccessible-subtree failure was not reproduced. A passing synthetic/mock test is not proof of non-root behavior.
- The documented state digest detects accidental or uncoordinated edits, **not** an adversary recomputing the hash.
- Durable local pending and repeatable JSON output **do not guarantee exactly-once external delivery**. The CLI has no downstream receiver and requires manual acknowledgment after reliable acceptance.
- Filesystem races, cross-platform behavior and unknown third-party runtimes are outside these tests.
- An exact source revision is VERIFIED; modified code does not inherit this designation.
- The overall kit remains PREVIEW. No owner-approved RELEASED tag, external intake integration or scheduled production execution is authorized by this verdict.

## Release follow-up
Test non-root inaccessible directories and verify an explicit nonzero error, not an empty observation. Preserve OS/Python/privilege information and source file SHA-256. Keep actual paths, configs, logs, pending messages and personal identifiers out of this public repository. Full release manifest and P5 owner approval remain open.
