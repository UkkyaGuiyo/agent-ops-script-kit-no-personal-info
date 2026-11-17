# 台帳係：独立検証概要（EVP/1 20261117-016）
**STATUS: VERIFIED, scoped; non-root access-denial case UNVERIFIED.**
**Tested revision:** `35f4d96694047f31080a8094e28da3863535e0d5`
**Date:** 2026-11-17 (JST)
**Source:** V.E.S.T.A.R.D.'s independent-test report EVP/1 `20261117-016`. The private full logs and full clean-room explanation were not transferred for direct review. This document is a summary of tester-reported measurements, not an independently rerun experiment by the editor.

## Reported tests
| Case | Measured/reported result |
| --- | --- |
| Fresh clone | HEAD equals `35f4d96` |
| Unit tests, entire kit | 34 / 34 PASS = 11 capacity + 23 ledger |
| Clean synthetic ledger | 4 entries, 0 issues, exit code 0 |
| File integrity | Ledger SHA-256 unchanged before/after; actual digest not supplied |
| Synthetic defective ledger | 8 entries, six fault categories distinguished |
| Defect categories | invalid_state, duplicate_title, missing_state, column_count, reference_missing, completed_retained |
| Invalid ledger format | exit code 2 |
| Unreadable ledger | JSON explicit error and exit code 1, fail closed |
| Clean-room AI explanation | Reporter judged PASS; explained form vs. actual completion, exit codes 0/2/1, --allow-completed, missing vs. unverifiable, privacy and pilot limitations |

## Material exception, not hidden
- **UNVERIFIED on a real restricted filesystem:** `reference_unverifiable`, because the tester ran as root and could not reproduce OS permission denial.
- **PASS in mocked unit test:** `test_unverifiable_reference` injects `PermissionError` into `Path.stat` and checks the `reference_unverifiable` category. This is a code-path test, **not** evidence of actual access denial in a non-root environment.
- Additional non-root test is recommended before a formally approved release. Record OS, Python version, privilege level, file-system permissions, the expected finding and observed exit code. Never publish real local path names or contents.

## Verdict and boundary
**E.L.I.S.: ACCEPT_WITH_CONDITIONS** for transition **PILOT → VERIFIED** on the tested commit and successfully exercised scope. The full project remains **PREVIEW**, not RELEASED. Code updates cannot inherit VERIFIED without a new verification record. No SHA-256 release manifest was created as part of this report.
