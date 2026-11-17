# P1：台帳係の公開用仕様確認
**STATUS: P1 accepted for public PILOT implementation; independent validation PENDING.**
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

## Next gate
V.E.S.T.A.R.D. performs a fresh-clone trial against the exact published commit, validates test counts and exit codes, checks file hashes before/after, and asks a fresh Muse to explain limits and risks to an inexperienced user. Only then is PILOT → VERIFIED eligible. The owner must separately approve formal RELEASED status.
