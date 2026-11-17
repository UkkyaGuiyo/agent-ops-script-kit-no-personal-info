# P1：台帳係の公開用仕様確認
**STATUS: P1 accepted; public implementation VERIFIED for commit 35f4d96 with non-root permission scenario unverified. See [verification summary](../verification/ledger-check-2026-11-17.md).**
**SOURCE:** V.E.S.T.A.R.D. generalized internal-spec report EVP/1 20261117-015 (no private source files examined by E.L.I.S.).

## Correction of previous hypothesis
The previously proposed **two-ledger comparator** was wrong. This public operator checks the **format of ONE Markdown task ledger**. It does not decide if a task is actually done, and never rewrites the ledger.

## U1–U4 decisions
- **U1:** Fixed four Japanese states in this pilot: 未投入, 実行中, 完了, 本人保留. Exact match only; no user-defined state mapping in this revision.
- **U2:** BOTH Markdown tables and top-level list items are supported.
- **U3:** Completed entries remaining in the ledger are flagged by default. General-purpose users may opt out with **--allow-completed**. This changes only this one check.
- **U4:** Permitted columns are exactly 作業, 状態, 承認・指示, 実体・根拠, 更新; required: 作業 and 状態. Other names or duplicates in an initial ledger-header candidate are errors.

## Compatibility boundary
- Later tables with a header different from the canonical header are ignored until a non-table line. Same-header unrelated tables cannot be distinguished from ledger tables.
- Top-level dash/star/plus Markdown bullets outside fenced code are considered candidate task entries. Use indented lines for task details. Unrelated bullets may be flagged.
- Absolute/home relative path checks are conservative, platform-dependent metadata checks. Unsupported path forms are ignored.
- JSON reports may contain local task titles and paths: NEVER share them publicly.
- Inaccessible input returns exit code 1; an examined ledger with findings returns exit code 2; clean result returns 0.

## Verification disposition
V.E.S.T.A.R.D. reported a fresh-clone test of commit 35f4d96, 34/34 tests PASS for the combined kit, clean synthetic ledger (4 entries, 0 issues), abnormal synthetic ledger (8 entries), expected exit codes and clean-room AI explanation. The live non-root reference_unverifiable path was not executed; a mocked PermissionError test did PASS. The status VERIFIED is scoped, not universal. The owner must still approve any formal RELEASED tag.
