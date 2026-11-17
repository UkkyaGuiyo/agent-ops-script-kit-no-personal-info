# 投入量見張り係：独立検証概要（EVP/1 20261117-022）

**Date:** 2026-11-17 (JST)  
**Tested commit:** `a60df96b17875e0c49f07b5beafa9fd04469b9ee`  
**Verdict:** E.L.I.S. ACCEPT_WITH_CONDITIONS; PILOT → VERIFIED within tested source revision and environment.  
**Reporter environment:** Linux/root; other OSs, non-root and large inputs UNVERIFIED.

**Evidence provenance:** These are **V.E.S.T.A.R.D.'s independently reported observations** from a fresh clone, not a claim that E.L.I.S. executed the tester's private CLI. The tester's full local logs and fresh-Muse explanation were not published. E.L.I.S. separately reread the public Python implementation and its local unit tests. There are no private paths, source content or operating records in this summary.

## Reported observations

| Criterion | Result | Evidence status |
| --- | --- | --- |
| Fresh clone identity | HEAD matches `a60df96` | PASS (reported) |
| Whole-kit test suite | **168/168 PASS**, prior 116 + injection-size 52 | PASS (reported) |
| Synthetic byte anchor | 120 B Markdown + 129 B JSON = **249 B** | PASS (reported) |
| Model tokens | `token_count=UNKNOWN`, no byte-to-token conversion | PASS (reported) |
| Initial weekly comparison | `UNKNOWN_NO_BASELINE` | PASS (reported) |
| Exact per-file size limit | 100/100 B is not over limit | PASS (reported) |
| One byte over size limit | 101/100 B gives `status=warning` and a private backup/audit/classification/drafts/comparison/self_test/manifest package | PASS (reported) |
| Source integrity | Source SHA-256 unchanged before/after warning generation | PASS (reported) |
| Missing target | Reports partial measured targets, `total_bytes=null`, no history advancement, exit 1 | PASS (reported) |
| Changed configuration | `Marker or configuration mismatch`, exit 1 | PASS (reported) |
| Weekly derived growth **exactly 10%** | Not independently reproduced through live CLI due to inability to recompute valid history-integrity hash; source's `Decimal` comparison was reviewed, and production-side unit tests include the boundary | **UNVERIFIED for independent CLI execution** |
| Fresh Muse explanation (C-7) | Reporter assessed PASS for exact bytes vs UNKNOWN tokens, never applying drafts, new public A–F labels, `NOT_ASSESSABLE` semantic reproduction, text drafts unchanged, private full-text backup | PASS (reported) |

## Boundary decision

The project P0 status `VERIFIED` refers to a **scoped independent validation**, not proof on every OS or every boundary. Direct source inspection confirmed `pct > Decimal(str(threshold))`, and `tests/test_injection_size_watch.py` contains a 100 B to 110 B over seven days test with no warning. This supports the implementation choice but is **not equivalent** to a separately reproduced independent CLI boundary measurement. The exception remains open, rather than being erased by the reported 168/168 test pass.

Source and draft file hashes identify bytes, **not** whether a draft preserves human-relevant meaning. The semantic/key-point reconstruction status is `NOT_ASSESSABLE`. A JSON whitespace-only example is not evidence of model token savings or semantic compression of real documents.

## Remaining gates

- Reproduce exact weekly growth threshold on a fresh, valid CLI-run history without manual hash manipulation; preserve test setup and measured output.
- Test non-root permission-denial behavior, any platforms proposed for release, and representative larger data sets.
- Freshly verify public release manifest and anchor checks, review safety and license; obtain separate owner approval for P5.
- Do not publish real config paths, source files, backup packages, draft contents or logs. Do not automate draft application, deletion, external delivery or scheduling.

**Overall kit status:** PREVIEW; no human-approved `RELEASED` tag.
