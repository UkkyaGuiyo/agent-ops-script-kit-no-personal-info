# Agent Ops Script Kit | P4再監査・第2回（EVP/1 20261117-072）

- **Date:** 2026-11-17 JST
- **Review target (immutable code/document tree):** `4daf2388d8aa32c870679a35a893373d35a236eb`
- **Prior correction commit:** `89dffe10d858edb6c0db09014457444868c87793`
- **Repository:** `UkkyaGuiyo/agent-ops-script-kit-no-personal-info`, public `main`
- **VERDICT:** **ACCEPT_WITH_CONDITIONS** for the post-correction P4 recheck. **The unconditional P4 release gate remains OPEN; P5 remains BLOCKED.** This is NOT a formal release or an instruction to tag.
- **BASIS:** `SPEC_P0.md`; [P4 round 1](p4-audit-round1-2026-11-17.md); [remediation checklist](p4-remediation-checklist-2026-11-17.md); [option A implementation note](p4-privacy-a-implementation-2026-11-17.md); GitHub API reads of the exact target and reachable public main history; independent test-reporting AI's EVP/1 20261117-072 report.
- **SCOPE:** tracked HEAD files, 29 reachable public main commit patches and commit metadata, source-license headers, approved historical-identity exception, static security and release-readiness checks. Private records and operational deployment are not audited.

## Evidence inventory

1. The README explanation requested in EVP/1 20261117-072 was appended **verbatim**, in a normal distinct commit `4daf2388d8aa32c870679a35a893373d35a236eb`, after correction `89dffe1`. Read-back Git blob SHA: `2c5c71e9c0148f7deda2525f4a6616a599348d39`. The commit patch changes **README.md only**. Existing README content and other tracked files were not edited by this explanatory commit.
2. HEAD Git tree listing was **not truncated**: **143 tracked file blobs**, **29 directory trees**, **172 total tree entries**, and **850,581 B** summed tracked blob bytes. Every blob was fetched separately via the connected GitHub service and its decoded UTF-8 byte length compared to the tree size: **143/143 size matches**. All file modes were regular files (`100644`); no tracked symlink/submodule was listed. These byte-length checks are **not** an SHA-256 release manifest.
3. GitHub listed **29 reachable commits**, **one branch (`main`)**, **0 tags**, **0 releases**, **0 pull requests**. All 29 commit patches were fetched and all changed-file entries had text patches. Public author metadata used a GitHub noreply address and one author alias; the first platform commit also used GitHub system committer metadata. This metadata is not private-user anonymity.
4. Current HEAD source scan: restricted distinctive AI names/variants **0 outside the approved README explanatory section**; that one section contains **4 explicit occurrences** under the owner's narrow, declared exception. Prior public history still contains the aliases and is **intentionally retained** under option A. No rebase, force-push, object deletion or history rewrite occurred. This exception does not permit human identity, credentials, private logs, private prompts, real account IDs, or other undisclosed identifiers.
5. Head files and all 29 public patches were screened for selected token/credential patterns, real-form email candidates excluding reserved `.invalid` examples and GitHub noreply metadata, and selected personal home-directory paths. No substantiated private credential/contact/path match remained under those patterns. One apparent email match in a patch was the Python decorator `@contextlib.contextmanager` and was rejected as a false positive. Pattern scanning cannot prove universal absence of personal data or third-party source copying.
6. **24/24 tracked Python files** contain `SPDX-License-Identifier: GPL-3.0-only`. The correction commit's **12 affected Python file patches** add exactly two copyright/SPDX comment lines with no removals or executable-body edits. Shebangs, module docstrings and `from __future__` ordering remain intact. The original tracked GPLv3 LICENSE blob remains `f288702d2fa16d3cdf0035b15a9fcbc552cd88e7` (**35,149 B**).
7. The **12 runtime scripts** were re-read for obvious outbound/network imports, shell subprocess imports/calls and dynamic execution signatures; none of the searched signatures appeared. The Retention Manager still requires an explicit `--apply` for synthetic staging/restore and exposes no `purge` command. This is static evidence only, not a dynamic security or race-condition proof.
8. The independent test-reporting AI reported a **fresh clone pinned at `89dffe1`**, **618/618 PASS, 0 SKIP**, `compileall` OK, 24/24 SPDX, semantics spot review, and synthetic Retention Manager `init → preview → stage → restore → preview` with restored payload SHA-256 match. No runtime code or test body changed in the subsequent README-only commit. **Those independent runtime results are accepted as attributed reports, not newly executed by this auditor.** Git clone and local test execution were unavailable in this auditor's execution environment.

## CRITERIA

| ID | Judgment | Reason / boundary |
| --- | --- | --- |
| S1 | **PASS (static scope)** | No new runtime logic; source signatures rechecked across 12 scripts |
| S2 / SEC-LIMIT | **PASS_WITH_LIMITATIONS** | Synthetic-only guardrails and explicit apply; marker, TMPDIR, symlink/race/crash limitations remain |
| P1 | **PASS_WITH_LIMITATIONS** | 143 HEAD blobs + 29 history patches screened with stated patterns; no universal secrecy proof |
| P2 / PRIV-01 | **PASS (declared exception)** | Owner-approved option A; no current residual except README; historic aliases permitted, no rewrite |
| L1 | **PASS** | GPL-3.0-only repository license unchanged |
| L2 / LIC-01 | **PASS (file-header scope)** | 24/24 Python SPDX; 12 header-only changes, executable bodies untouched |
| G1 | **PASS_WITH_LIMITATIONS** | 29 reachable main commits and metadata checked; unreachable objects, mirrors and public forks not exhaustively inspectable |
| R1 | **PASS_WITH_LIMITATIONS** | PREVIEW, no release tag; known scope and independent test-reporting limitations retained |
| PROV-01 | **UNRESOLVED** | Owner/rightsholder authorship permission and any externally borrowed source attribution still require explicit confirmation |
| REL-01 / R2 | **PENDING** | Frozen all-file SHA-256 manifest and independent full rehash not yet performed |
| P4-RECHECK | **COMPLETE for target** | This report records the recheck on `4daf2388d8aa32c870679a35a893373d35a236eb`; adding this report creates a separate evidence-only Git commit |
| P5 | **BLOCKED** | No human-approved manifest-backed formal release |

## CONDITIONS

- **C-1 / PROV-01:** Before an unconditional P4/P5 clearance, obtain and record explicit owner/rightsholder permission to distribute the code and text under GPL-3.0-only; disclose and resolve any copied/externally licensed source identified. Static no-dependency screening is not an authorship attestation.
- **C-2 / REL-01:** Freeze the exact candidate commit; enumerate all tracked regular files and generate a complete per-path **SHA-256 + byte-size manifest** with source commit, UTC generation time, count and blob identifiers. Do not self-hash the manifest. Save it separately, then have the independent test-reporting AI recalculate every file hash and the required anchors in a fresh clone. If any candidate bytes change, regenerate and repeat the audit.
- **C-3 / audit continuity:** The audit-record commit must not change code or the reviewed README. Keep the release subject tied to the pinned reviewed tree, not to an unverified later branch tip. Recheck any future code/content edits before a final unconditional verdict.
- **C-4 / safety:** No production filesystem apply, live Gmail/Notion binding, real-account operation, deletion, history rewrite, public release tag or other irreversibly consequential operation follows from this report.

## OUT_OF_SCOPE

Raw private execution transcripts, independently rerunning 618 tests in this auditor environment, non-root/Windows/NFS behavior, actual emails/Notion credentials, real-root staged cleanup, complete crash/race recovery, full code-similarity review, all unreachable Git objects, outside forks and formal legal advice.

## UNRESOLVED

`PROV-01` and `REL-01` remain open. Non-production safety limitations persist as documented limitations rather than a newly authorized implementation request. The final P4 release gate is **not ACCEPT** until mandatory requirements have PASS evidence and unresolved blockers are NONE.

## Final EVP/1

- **VERDICT:** ACCEPT_WITH_CONDITIONS (post-correction recheck only)
- **BASIS:** exact `4daf2388d8aa32c870679a35a893373d35a236eb` and the sources enumerated above
- **SCOPE:** current tree + reachable public main history, GitHub API static review, attributed independent runtime report
- **CONDITIONS:** C-1 through C-4
- **OUT_OF_SCOPE:** as specified above
- **UNRESOLVED:** PROV-01; REL-01
- **P4_GATE:** OPEN, unconditional ACCEPT not yet issued
- **P5:** BLOCKED; no release/tag authorization
- **RESPONSE_STATUS:** COMPLETE (this README + recheck work order); evidence/approval pipeline continues separately

Next permitted step: **REL-01 evidence production** after a clear candidate freeze. This permission is to prepare and verify evidence, NOT a release decision.
