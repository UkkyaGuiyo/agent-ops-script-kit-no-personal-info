# 第6号 整理係：独立検証概要（EVP/1 20261117-028）

**Date:** 2026-11-17 (JST)  
**Tested commit:** `84ca9fe08fb21658fab05e99a5029f55ee2d56ab`  
**Verdict:** E.L.I.S. `ACCEPT_WITH_CONDITIONS`, PILOT → VERIFIED for this code revision and measured runtime scope.  
**Tester:** V.E.S.T.A.R.D. (Linux/root environment).

## Evidence provenance
These results are **independently reported measurements from a fresh clone by V.E.S.T.A.R.D.**, not tests executed directly by E.L.I.S. The full tester logs and C-7 explanation were retained in a private verification file; they were not published or directly inspected here. E.L.I.S. separately reread the exact public technical specification, `scripts/organizer.py` and its 55 test definitions. No private filesystem paths, account data, actual filenames or log extracts are disclosed.

## Observed and reported results

| Criterion | Result | Evidence state |
|---|---|---|
| New clone and commit | HEAD equals `84ca9fe08fb21658fab05e99a5029f55ee2d56ab` | PASS (tester report) |
| Entire project test suite | **223/223 PASS** = prior 168 + organizer 55 | PASS (tester report) |
| No mutation authority | No `apply`, `purge` or `move` commands. Output explicitly `dry_run=true`, `trash_move_available=false`, `purge_available=false`, `deletion_available=false`, `changed_files=0` | PASS (tester report and source inspection) |
| Disposal threshold at 14 days | `disposable` and exactly 14 × 24 hours → `candidate` | PASS (tester report) |
| Just short of threshold | `disposable` and 13 days 23 hours → `not_due` | PASS (tester report) |
| Permanent classification | `permanent` + 14 days → `excluded` | PASS (tester report) |
| Unknown tag class | `hold`, reason `UNKNOWN_TAG_CLASS` | PASS (tester report) |
| Missing registered file | `hold`, reason `MISSING_REGISTERED_FILE` | PASS (tester report) |
| Outside-root record path | `hold`, reason `UNSAFE_RECORD_PATH` | PASS (tester report) |
| Unregistered file | Not inspected or output; `unregistered_files_scanned=false` | PASS (tester report) |
| Incomplete result | Any hold leads to `status=partial`, exit 1, not a normal clean/empty report | PASS (tester report) |
| Source and records unchanged | SHA-256 of all files in synthetic root unchanged before/after | PASS (tester report) |
| C-7 fresh Muse explanation | All five requested points passed according to tester | PASS (tester report) |
| Non-root, Windows, other filesystem | Not independently tested | UNVERIFIED |

## Scope and cautions
The operator's word **Organizer** refers to a **file-lifetime preview**, not automatic categorization into folders. It uses creator-declared `disposable`/`permanent` records and each registered file's mtime only. A `candidate` is never itself approval to trash, move, overwrite or delete. The public code does not implement any mutation commands, scheduling, tagging or external delivery. The internal system's later 1-month purge and shared-intake's 90-day retention must not be conflated with the proposed 14-day threshold.

The independent reporter's environment was Linux/root. Live non-root permission failure, Windows, networked filesystems, very large records, concurrent filesystem changes, or equivalence with private operations remain **UNVERIFIED**. SHA-256 demonstrates byte identity, not semantic validity. The repo remains **PREVIEW** and lacks the owner's separate P4/P5 release approval.
