# 台帳係：単一Markdown台帳の形式チェッカー
**STATUS: VERIFIED for commit 35f4d96694047f31080a8094e28da3863535e0d5, except live non-root permission-denial behavior (UNVERIFIED). Not RELEASED.**
**License:** GPL-3.0-only. Independent public implementation based on generalized requirements, not copied private code.

## Scope
Input: **one** local UTF-8 Markdown file. The program checks syntax and specified local references. It does **not** compare two ledgers, edit files, repair them, prove task completion, use AI, communicate over a network, or schedule execution.

## Accepted forms
**Table:** first candidate with a header and immediately following Markdown separator establishes canonical columns through EOF. Required: 作業 and 状態. Optional: 承認・指示, 実体・根拠, 更新. Duplicate and unknown column labels in an initial candidate are invalid. Blank optional cells are allowed. Column order is fixed by the first valid header. Later matching headers count as the same ledger; differing headers and their rows are ignored until a non-table line. Ordinary non-table lines, blank lines and lists do not cancel the canonical header.

**List:** top-level Markdown bullets with -, + or * followed by a space, then [状態] and a nonempty title. Subsequent lines indented at least two spaces are considered description. [合図待ち] may precede or follow [状態], and is **not a state**. A missing state marker is reported. Unrelated top-level bullets can be mistaken for tasks.

**Fenced code:** triple or longer backtick/tilde fences are skipped. Markdown table cells use unescaped pipes as separators; an odd number of preceding backslashes escapes a literal pipe.

## States
Only these four strings are valid: 未投入 / 実行中 / 完了 / 本人保留. The last means waiting for the owner's restart instruction, not an invitation to automatically chase the owner.

## Findings
- duplicate_title: same trimmed task title occurs more than once, across both formats
- invalid_state: state differs from fixed vocabulary, including partial matches
- missing_title, missing_state: mandatory title or state absent
- column_count, invalid_header: row columns wrong, or initial candidate header has unknown/duplicate/missing columns
- reference_missing: recognized local absolute/home path not found
- reference_unverifiable: permission/OS failure prevents checking a recognized path
- completed_retained: task still marked 完了; default on, bypass ONLY with --allow-completed
- duplicate_wait_marker: repeated [合図待ち]

**Path boundary:** only native absolute paths or ~/ paths with conservative recognition are considered. Relative references, bare filenames and other OS path syntaxes are excluded. Backtick quotation allows a path with spaces. Metadata existence is not proof of content quality. Filesystem changes during scanning can affect results.

## Output and exit codes
**stdout JSON** with status=ok|issues|error, entries count and issues array when input is read successfully. Findings include type, line and title (sometimes path). **0** = complete examination without findings; **2** = findings; **1** = file unreadable or decoding failure, status=error, no normal measurement. JSON output may contain sensitive local titles and paths: keep it off GitHub.

## Safety and recovery
Read-only; no network or elevated permissions. Does not alter the ledger. Stop by ending the process. No rollback needed. A human reviews any corrections. No content-based verification of actual work is provided.

[HowTo](../howto/ledger-check.md) / [初心者向け説明](../explain/ledger-check.md) / [P1決定](../plans/ledger-checker-pilot.md) / [独立検証概要](../verification/ledger-check-2026-11-17.md).
