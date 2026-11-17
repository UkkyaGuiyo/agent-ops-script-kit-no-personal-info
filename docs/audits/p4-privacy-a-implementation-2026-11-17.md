# P4-PRIV-01 + P4-LIC-01：方式A・内容修正の実施記録

**2026-11-17 JST** | **OWNER DECISION:** option A, current-tree redaction only; historic published names expressly allowed to remain. **No force push, no rebase, no history rewrite, no old-object deletion.**

**Approval provenance:** EVP/1 `20261117-066`, the separate reporting AI relayed the owner's definitive selection at 15:08 JST and follow-up at 15:09 JST. The owner treats old aliases as innocuous historic proper nouns and permits their retention in prior public commits. This is a documented **narrow exception**, NOT approval to publicize actual human identity, credentials, internal source data, private logs or future new aliases. GitHub public account handle, noreply author metadata and commit author are outside the redaction scope.

## Scope of the single normal commit
- Target original tree: `2014955a5ee0b628790593e5d4cf21d610d9a6c0` (proposal commit, before edits).
- **39 Markdown files**: role-sensitive replacements for the two internal agent codenames and their short/colloquial variants; originally **37 files / 109 full-name instances + 6 additional short-name instances** across two existing and two extra files = **39 unique files / 115 total instances**.
- Exact design/implementation/audit role is distinguished from (i) the generalized private-spec reporting role and (ii) fresh-clone independent test-reporting role. Evidence remains attributed as `reporter-reported` where the implementation AI did not run the original private tester commands or inspect private C-7 transcripts.
- **12 Python files**: 3 scripts and 9 tests gain exactly `Copyright (C) 2026 Contributors to Agent Ops Script Kit` and `SPDX-License-Identifier: GPL-3.0-only` as source comments, with the shebang and all source body bytes otherwise unchanged. Do not add or infer third-party ownership.
- This note and the P4 remediation checklist record the status. The pre-approval proposal and round-one P4 audit are historical records, not current P4 acceptance.

## Expected independent verification
1. Fresh clone at the exact resulting correction SHA; read back HEAD and validate **no restricted codenames or short/colloquial variants in current tracked files**. The historical aliases remain intentionally in pre-correction commits; do not claim their removal.
2. Verify semantic attribution on P1 specs and P3 reports: design/authoring, private-spec report, separate testing report, evidence re-read limitations, original test-commit SHAs and numerically typed anchors must be unchanged.
3. Verify **24/24 tracked Python files** carry the declared SPDX notice; compare the 12 modified Python bodies before/after stripping only the new two-line header, and verify shebang/module docstring/future-import legality.
4. Fresh-clone `python -m unittest discover -s tests -v` **618/618 PASS, 0 SKIP** and `python -m compileall -q scripts tests`; confirm related C-7 explanations and synthetic retention stage/restore remain valid. **These are REQUIRED FOLLOW-UP TESTS, not claims of already completed tests at the new SHA.**
5. Source and current-public-history privacy recheck; mark old-code-name residual only as the owner-approved explicit exception. Reassess copyright provenance and complete release SHA-256 manifest separately after freeze.

**P4 remains REVISE and P5 remains BLOCKED** until independent retest, renewed P4 adjudication, complete candidate manifest and author/rightsholder clearance. No release tag is approved or created.
