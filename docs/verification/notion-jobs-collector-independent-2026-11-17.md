# 第9号 Notionジョブ収集係：独立検証概要（EVP/1 20261117-041）

**Date:** 2026-11-17 (JST)  
**Tested code revision:** `0eade24b0e174f67ee5c9859cc6a8621cf321721`  
**Verdict:** the public design/audit AI `ACCEPT_WITH_CONDITIONS`, PILOT → VERIFIED **only for this revision's reported Linux/root offline fixture scope**.  
**Evidence provenance:** These are the independent test-reporting AI's measurements **reported from a fresh clone**. the public implementation AI independently reread the public source, tests, specifications and producer verification report but did not run the tester's private CLI or read the full C-7 explanation transcript. All fixtures described here are synthetic; do not publish private task/page data.

## Reported independent results

| Criterion | Observation | Assessment |
| --- | --- | --- |
| Exact commit identity | Fresh clone HEAD `0eade24b0e174f67ee5c9859cc6a8621cf321721` | PASS (reported) |
| Whole-kit tests | **441/441 PASS**, existing 370 + Notion collector 71, **0 SKIP** | PASS (reported) |
| Shared Intake v1 validation | The public `validate_item` compatibility test, skipped in producer-only environment, actually executed and passed | PASS (reported) |
| check before bootstrap | `BOOTSTRAP_NOT_COMPLETE`, `error`, exit 1 | PASS (reported) |
| First bootstrap | 1 baseline date page, 1 baseline URL, new events 0 | PASS (reported) |
| Repeated bootstrap | `BOOTSTRAP_ALREADY_COMPLETE`, exit 1 | PASS (reported) |
| First updated check | **3 events** (new date page 1 + added URLs 2), pending 3 | PASS (reported) |
| Repeated updated check | New events 0, pending still 3 | PASS (reported) |
| Candidate schema/provenance | All three pending proposals conform to Shared Intake v1 validation, carry policy version and SHA-256, mark "offline local preview; not delivered" | PASS (reported) |
| External operations | `shared_intake_write=false`, `external_delivery=NONE`; only local JSON fixture provider exists in public code | PASS for intentional non-features |
| Fresh-Muse C-7 explanation | All 5 required boundaries plus explicit lack of global cross-page URL deduplication | PASS (reported) |
| Cross-page global URL deduplication | Currently keyed by page ID + normalized URL; whether the private operational requirement needs global dedup is unresolved | UNKNOWN / UNRESOLVED |
| Non-root, Windows/macOS, real Notion API/CLI, real Shared Intake delivery, large data | Not tested or not implemented | UNVERIFIED / OUT_OF_SCOPE |

## Scope and remaining risk
**Notion is the input source only for the reported private implementation**. The public script includes a `PageProvider` interface but bundles **only an offline synthetic `FixtureProvider`**. It makes no network calls, holds no Notion credentials, does not read or write real Notion pages, and has no Shared Intake sender. A locally persisted `pending` candidate proves neither actual inbox acceptance nor user review/job application.

`bootstrap` records a one-time baseline. An incomplete initialization blocks `check`; a completed bootstrap cannot be silently replayed. A failed parent response is `error`, a failed child response yields `partial` with retry, not "zero new jobs". Conditions are a strict limited YAML subset validated by version/hash; this is not a general YAML parser. The public duplicate key is page ID + normalized URL: two date pages may legitimately generate separate candidate records for the same URL. This may require a separate future feature design but does not contradict the current published specification.

No account connection, live page collection, global URL dedup guarantee, inbox delivery, notification, scheduling or application is approved by this verdict. The kit remains **PREVIEW**, with P4 security/license/history/release audit and independent P5 owner approval outstanding.
