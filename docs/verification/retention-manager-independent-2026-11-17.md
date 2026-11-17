# 第11号 保持管理係：独立検証概要（EVP/1 20261117-051）

**Date:** 2026-11-17 JST
**Exact tested source commit:** `992e1e6430788514b5c9e19c66036a080bd592dd`
**Verdict:** E.L.I.S. ACCEPT_WITH_CONDITIONS; PILOT → VERIFIED only for the tested Linux/root synthetic OS-temp demo scope.
**Provenance:** V.E.S.T.A.R.D. reported independent new-clone tests, synthetic CLI anchors and C-7 explanation. Private full logs and C-7 transcript were retained by the tester and not inspected by E.L.I.S. E.L.I.S. separately reread the exact public source revision, test definitions, contract and producer evidence. This is not an independent re-execution of the tester's checks by E.L.I.S.

| Criterion | Reported observation | Assessment |
| --- | --- | --- |
| Clone identity | HEAD matches `992e1e6430788514b5c9e19c66036a080bd592dd` | PASS (reported) |
| Whole-kit tests | **618/618 PASS** (previous 539 + retention 79), **0 SKIP** | PASS (reported) |
| Organizer actual source integration | Previously skipped public Organizer compatibility test executed and passed | PASS (reported) |
| `demo-init` | Four fictional files; three registered; physical deletion 0, `purge_available=false` | PASS (reported) |
| `preview` | candidate 1 (15 days), not_due 1 (13 days), excluded 1 (`permanent`), hold 0 | PASS (reported) |
| Dry-run and unregistered file protection | `records_changed=0`; unregistered files not scanned | PASS (reported) |
| `stage --apply` | Exactly one dated trash move with manifest; permanent/not_due/unregistered stay unchanged | PASS (reported) |
| Physical deletion | `physical_deletion_count=0`; `purge` not implemented and CLI rejects it | PASS (reported) |
| `restore --apply` | Exactly one item restored, SHA-256 equals recorded moved payload; post-restore preview matches initial | PASS (reported) |
| C-7 comprehension | All five checks: creator tag, Organizer proposal vs demo stage, conditional restore, purge absent, permanent/canonical data protected | PASS (reported) |
| Interruptions and crash-consistent recovery | Not verified | UNVERIFIED |
| Non-root, other OS, NFS, large real data | Not verified or not permitted | UNVERIFIED / OUT_OF_SCOPE |

## Decision boundary
The public Retention Manager can operate only on a freshly initialized **synthetic OS-temp demo root**, and only stage and restore fictional registered single-link regular files with explicit `--apply`. The creator's `disposable/permanent` tag and file mtime determine age; default 14 days, configurable. The public source does **not** include physical purge, one-month trash expiration, arbitrary live-root cleanup, tag reclassification, background schedules or cross-service access.

`staged` is not `purged`. `restore` works conditionally when payload integrity checks pass and the original location is vacant. SHA-256 demonstrates byte matching, not complete semantic recovery. This report **does not** establish automatic recovery from an interrupted `prepared` manifest, external process races, power loss, non-root restrictions or network filesystem behavior. Unknown, missing, permanent and unregistered data must not be treated as safe deletion candidates.

All **11 P0 operators now have independently reported scope-limited VERIFIED results**. The whole kit remains **PREVIEW**; the P4 security/license/privacy/Git history/release audit is **PENDING**, and explicit separate P5 owner approval is **PENDING**. Neither a tag nor a RELEASED claim is authorized by this report. P4 findings may require fixes and retesting before P5.
