# Agent Ops Script Kit | P5 正式リリース承認の記録

- **Protocol:** EVP/1 `20261117-086`
- **Reported owner decision time:** 2026-11-17 16:09 JST (07:09 UTC)
- **Decision:** Owner expressly approved a **formal tagged release** of the exact previously audited, limited-scope kit.
- **Approval channel/evidence:** A separate authorized assistant relayed the owner's explicit choice; this GitHub record is a report of that approval, **not an independent log of the human's UI action**.
- **P4 verdict:** `ACCEPT` / CLOSED for the frozen candidate, per [P4 final audit](../audits/p4-audit-final-2026-11-17.md).
- **P5 approval:** **ACCEPTED** for the identified release subject, not a permission for arbitrary future changes.
- **Tag creation:** **SEPARATE MECHANICAL STEP**. This document does **not** certify that the tag already exists. Confirm a tag by querying Git refs after creation.

## Approved release identities

| Role | Immutable commit |
| --- | --- |
| Source candidate C (143 regular files, 850,581 B) | `4daf2388d8aa32c870679a35a893373d35a236eb` |
| Manifest M (child of C; complete file hashes) | `087873bc9d44e2061818cb7c97ea77506b54b334` |
| P4 final audit record on former `main` | `f4f9c961b997b1ead94ebffbb00a2990a9da4fc4` |
| Non-code integration of manifest into `main` | `b32817d42ce26f6df3ec7a673b6da75a62d62357` |

- **Manifest path:** `docs/verification/rel01-full-tree-sha256-2026-11-17.tsv`
- **Manifest blob SHA-1:** `0cdd5640edf757445e2f763e690847ba2c02c8ee` (22,056 B)
- **Independent REL-01 verification:** 143/143 matching SHA-256 values, byte sizes and blob IDs; three independent anchors PASS; no missing or extra files, as reported under EVP/1 `20261117-081`. The P4 final audit attributes this evidence to its actual reporter.
- **Source provenance:** The rightsholder confirmed authority to distribute code/text under GPL-3.0-only and no copied third-party code; this is an owner attestation, not a legal opinion.

## Release content and historic statuses

At the approved scope, the release contains C's exact **unchanged code and documentation**, the verified REL-01 manifest M, the P4 final audit record and this P5 approval record. The integration commit b32817d42ce26f6df3ec7a673b6da75a62d62357 has two parents, P4-final `main` and M, and changes only the addition of the existing verified manifest blob.

The owner was explicitly told that `README.md`, `SECURITY.md` and `SPEC_P0.md` include **historical P4 REVISE / PREVIEW wording**, and approved this release **without updating those frozen source files**. The operative P4 decision is the dated **final P4 ACCEPT** record linked above. This approval does not authorize rewriting those files or changing any C payload bytes. Correcting release-facing wording later requires a separate frozen candidate, manifest and independent verification.

**This is an approved release of a deliberately bounded demo-oriented kit, not a certification for production, actual account integrations, or live file deletion.** In particular, the retention demo is restricted to freshly generated fictional files under an OS-temp demo root with explicit `--apply`. Crash interruption, adversarial concurrency, non-root and cross-platform behavior remain outside validated scope. History retains owner-approved internal AI aliases; no public Git history rewrite was approved.

## Tagging decision and verification handoff

- **Proposed first formal tag:** `v0.1.0` (first published, deliberately limited-scope kit; this version label is not a claim of production readiness).
- **Required tag target:** the immutable commit containing this P5 approval record **after** the manifest M was merged into `main`, with no further code changes. Obtain and pin the exact commit SHA when that record is committed.
- **Verification:** Confirm that the tag's peeled target equals that pinned SHA, the tag tree contains this approval record, the P4 final audit and the manifest at the exact expected blob, and all 143 frozen C source blobs are identical. Confirm GitHub reports the new tag ref.
- **No authorization beyond this scope:** no force-push, history rewrite, deletion, branch visibility change, production deployment or unrelated publication.
