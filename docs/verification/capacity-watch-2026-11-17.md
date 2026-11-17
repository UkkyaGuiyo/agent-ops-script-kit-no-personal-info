# Capacity watcher independent verification summary / 独立検証概要

**Status:** VERIFIED (reported independent tests; scoped to tested revision)
**Date:** 2026-11-17 (JST)
**Tested commit:** `e573312a0a15ed359cc273d7001cf304c77e1bfc`
**Source:** the independent test-reporting AI, EVP/1 report `20261117-014`. This document records the reporter's results; raw execution logs and full AI explanations were not supplied for public review. This is **not** a claim of direct re-execution by the person recording this summary.

## Reported measurements
| Test | Reported result |
|---|---|
| Fresh clone | HEAD equals tested commit |
| Python unit tests | 11 / 11 PASS |
| Example scan | status ok, 65 bytes, exit code 0 |
| Read-only behavior on target | SHA-256 unchanged |
| Git working tree | clean |
| Invalid configuration | explicit error, exit code 2, no normal measurement |
| Missing directory | not interpreted as 0 bytes |
| Fresh-AI explanation | model without prior project context explained preview status, sole implemented operator, errors, safety limits, personal-data prohibition, manual-only operation, no deletion, and no support guarantee; reporter judged PASS |

## Scope of VERIFIED
The tested revision contains a read-only, manually invoked Python watcher summing apparent file sizes of regular files. The reported results support this specific behavior on the tester's environment only.

## Exclusions and caveats
- Not a formal RELEASED version; the full kit remains PREVIEW.
- The source machine's full OS/Python/build environment and verbatim AI explanation were not provided in this report.
- The scan is not an atomic filesystem snapshot; special files are ignored; symbolic links are excluded; actual disk allocation and free disk space are not measured.
- The data is based on the independent tester's stated measurements, not direct access to their original records.
- No raw logs, private directories, real account information, names of personal files, or credentials belong in this repository.

## Follow-up
An independent release audit and SHA-256 file manifest remain required before the owner's formal P5 release approval. Future code revisions require their own verification evidence.
