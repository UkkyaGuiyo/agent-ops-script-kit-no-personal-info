# P4再監査チェックリスト（2026-11-17）

**Scope:** reference baseline `13847ed407cdfe51b2a227f3240b56349324546b`. This checklist is **not** a release authorization. Full [P4 findings](p4-audit-round1-2026-11-17.md).

| ID | Owner | Action | Required objective evidence | State |
| --- | --- | --- | --- | --- |
| PRIV-01 | Human via V.E.S.T.A.R.D. | Decide whether already-public internal AI aliases and GitHub publisher metadata are permitted disclosures; if not, separately approve a redaction plan without automatic history rewriting | Scope-specific approval/decision record and current/history re-scan | OPEN |
| LIC-01 | E.L.I.S. | Normalize 12 missing per-file SPDX/copyright notices; no functional edit | File-level diff, 24/24 Python headers, clean clone 618/618 tests 0 SKIP, compileall | OPEN |
| PROV-01 | Human/auditor | Confirm rights to release source/text under GPL-3.0-only and document external borrowings if present | Attestation and attribution/license file updates if needed | OPEN |
| REL-01 | E.L.I.S. / V.E.S.T.A.R.D. | Generate a complete SHA-256 manifest after candidate freeze, independently rehash all files | Candidate commit + manifest commit, tracked file count/size/SHA-256, all pass + 3 anchors | OPEN |
| SEC-LIMIT | E.L.I.S. / auditor | Keep synthetic-only/non-production scope and known race/crash limitations explicit | README, SECURITY, operator docs agree; no live-root `--apply` added | OPEN limitation, not a newly authorized feature |
| P4-RECHECK | E.L.I.S. / V.E.S.T.A.R.D. | Recheck full public history including new commits; verify no tags/releases, run tests after edits, confirm disposition | New P4 report at final pinned SHA | PENDING |
| P5 | Human | Review release subject only after P4 ACCEPT | Human review card with immutable manifest and risks | BLOCKED |

## Nonnegotiable release handoff
An owner command merely saying “release everything” is not a substitute for an exact reviewed commit and its file SHA-256 manifest. Never infer approval for history rewrite, real account access, file deletion or external messages from this checklist. P5 remains blocked until the P4 gate is resolved.
