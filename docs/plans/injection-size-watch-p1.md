# 投入量見張り係 P1確定・公開版判断

**EVP/1:** 20261117-021 / 2026-11-17  
**Status:** P1 ACCEPT_WITH_CONDITIONS; public implementation VERIFIED for a60df96 (Linux/root test scope only). Weekly 10%-equality CLI independent check UNVERIFIED.

## Evidence boundary
V.E.S.T.A.R.D. explicitly confirmed **NO completed private automated implementation** existed at the time of the report. Input was the owner's established design and a single manually completed procedure. Neither private files nor their contents, local paths, prompts or raw measurement logs were transferred or copied. The public code was independently authored and is not a port from private source.

## U1–U3
- **U1 configuration:** JSON file list with per-file `limit_bytes` and a shared `weekly_growth_percent`. Suggested values: **60,000 bytes** (60 decimal kB, NOT 60 KiB) and **10.0%**. These are examples, not universally applicable maximums. A threshold is exceeded with `>` not `>=`.
- **U2 complete staged pipeline:** Public CLI measures exact bytes, and **when triggered** creates a dated private backup, audit, conservative A–F classification candidates, safe drafts, an actual byte comparison, and mechanical self-test. It **never applies a draft** to any monitored input. This is not a promise of useful text compression.
- **U3 public labels:** A=retain, B=JSON formatting-only candidate, C=condense after human review, D=move to on-demand after human review, E=remove after human approval, F=needs semantic review. **These are new, generalized public labels; the original private A–F definitions are UNKNOWN.** C/D/E are not automatically selected or applied. `.md`/`.txt` are copied unchanged and marked F by default to avoid unverifiable edits; parseable `.json` may be losslessly compacted and marked B.

## Source-derived rules vs public pilot decisions
- Source-derived: always-loaded context **file list**, not on-demand logs; file bytes authoritative; auxiliary characters/lines, **tokens UNKNOWN**; file limits and weekly growth; quiet measurements without warnings; staged drafts, no apply; failure never silently omitted; history of timestamps and byte sizes.
- Public design decision: only local `.md`, `.txt`, `.json` files up to 2,000,000 bytes each, strict UTF-8 and strict JSON where applicable; symlink path rejection; explicit private state directory outside the checkout; one-week comparison uses the most recent sample at least 7 days old. If no full week exists, `UNKNOWN` rather than an invented weekly estimate.
- Weekly rate is **derived by linear time normalization** of two exact byte readings: `(new−old)/old × 100 × 7days/observed_duration`. This is a mathematically calculated rate, NOT an observed model token count or a forecast. A separate last-measurement delta is reported. Daily measurement therefore does not disable weekly detection.
- Classification and mechanical self-tests do **not** prove semantic/key-point preservation. That output remains `NOT_ASSESSABLE` pending human/AI review. No self-assigned PASS may stand in for semantic review.

## Out of scope
No automatic editing/backup outside the user-designated private state directory, no scheduled runs, no external service/API, no AI content rewriting, no prompt injection detection, no sharing raw source text, no automatic state reset, no transfer of the private one-off result as a performance benchmark. The measurement mechanism uses only the standard library.

## Pilot test gate
Synthetic exact byte/Unicode totals, strict threshold boundaries, seven-day growth and daily cadence, unreadable/invalid/oversized inputs, per-file and whole-scan errors, hash and history corruption, marker missing, lock conflict, draft backup integrity and true byte comparison, JSON parsed-value equivalence, verbatim Markdown/text drafts, source SHA-256 unchanged, no path/content echoed, and clean-room Muse explanation. Only after an independent fresh clone may this operator become VERIFIED (scope-limited).

[Operator spec](../operators/injection-size-watch.md) · [HowTo](../howto/injection-size-watch.md) · [Beginner explanation](../explain/injection-size-watch.md).

## P3独立検証の追記（2026-11-17）
EVP/1 `20261117-022`: 新規cloneで全168/168件（既存116＋本係52）がPASSと報告された。合成アンカー249 B、上限100 Bちょうどで正常・101 Bで警告、原本SHA-256不変、部分失敗のtotal_bytes=null、設定不一致の明示的エラー、C-7説明再現PASS。週次増加率の**ちょうど10%**は実行環境から履歴整合性ハッシュの再現ができず**独立CLI実測としてUNVERIFIED**。Decimal比較は実装ソースで確認でき、制作側単体テストに含まれる。非root・他OS・大量ファイル・実運用、意味の保持は未実証。[独立検証概要](../verification/injection-size-watch-independent-2026-11-17.md)。
