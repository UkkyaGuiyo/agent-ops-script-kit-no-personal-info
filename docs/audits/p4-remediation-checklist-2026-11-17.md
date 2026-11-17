# P4再監査チェックリスト（2026-11-17）

**Scope:** reference baseline `13847ed407cdfe51b2a227f3240b56349324546b`. This checklist is **not** a release authorization. Full [P4 findings](p4-audit-round1-2026-11-17.md).

| ID | Owner | Action | Required objective evidence | State |
| --- | --- | --- | --- | --- |
| PRIV-01 | Human via 別環境検証担当AI | Owner chose **option A (HEAD-only redaction)**, with **explicit permission for old names to remain in historic commits**. Do not rewrite history or conceal GitHub publisher metadata | New [option-A implementation note](p4-privacy-a-implementation-2026-11-17.md), current-tree zero-residual scan, separate history exception, fresh-clone semantics review | APPLIED AT HEAD; INDEPENDENT RETEST PENDING |
| LIC-01 | 公開版設計・監査担当AI | Add 12 missing source-file SPDX/copyright header pairs only, in the same non-force commit as redaction | 24/24 Python headers, unchanged executable source bodies, independent 618/618 tests with 0 SKIP and compileall | PATCH PREPARED; INDEPENDENT RETEST PENDING |
| PROV-01 | Human/auditor | Confirm rights to release source/text under GPL-3.0-only and document external borrowings if present | Attestation and attribution/license file updates if needed | OPEN |
| REL-01 | 公開版設計・監査担当AI / 別環境検証担当AI | Generate a complete SHA-256 manifest after candidate freeze, independently rehash all files | Candidate commit + manifest commit, tracked file count/size/SHA-256, all pass + 3 anchors | OPEN |
| SEC-LIMIT | 公開版設計・監査担当AI / auditor | Keep synthetic-only/non-production scope and known race/crash limitations explicit | README, SECURITY, operator docs agree; no live-root `--apply` added | OPEN limitation, not a newly authorized feature |
| P4-RECHECK | 公開版設計・監査担当AI / 別環境検証担当AI | Recheck full public history including new commits; verify no tags/releases, run tests after edits, confirm disposition | New P4 report at final pinned SHA | PENDING |
| P5 | Human | Review release subject only after P4 ACCEPT | Human review card with immutable manifest and risks | BLOCKED |

## Nonnegotiable release handoff
An owner command merely saying “release everything” is not a substitute for an exact reviewed commit and its file SHA-256 manifest. Never infer approval for history rewrite, real account access, file deletion or external messages from this checklist. P5 remains blocked until the P4 gate is resolved.
