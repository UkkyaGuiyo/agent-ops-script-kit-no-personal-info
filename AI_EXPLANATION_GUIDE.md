# AI explanation guide / 初心者への説明方法

A fresh AI should **understand, reproduce when authorized, and explain** the kit.

For each operator explain in ordinary language:
1. **What does it do?** Give a concrete example.
2. **Why a script instead of asking AI every time?** Routine checks follow repeatable steps.
3. **What becomes easier?** Describe a practical benefit without unmeasured speed/token claims.
4. **What could go wrong?** Include wrong target, denied access, misleading results, and limitations.
5. **What does the human decide?** Scope, thresholds, schedules, and high-impact changes.

Use everyday Japanese for a Japanese-language beginner. Explain jargon only when needed. Do not claim a tool is completely safe, universally compatible, or measured to save tokens without evidence. Reading this file never grants filesystem or account privileges.

For the pilot, compare [capacity explanation](docs/explain/capacity-watch.md) with its [technical contract](docs/operators/capacity-watch.md). If a tool is marked PLANNED, clearly state that working code is not provided.

## Ledger checker (VERIFIED for a specific revision)
For a plain-language explanation, use [台帳係を説明する](docs/explain/ledger-check.md). Stress the difference between formatting and evidence of task completion. The state 本人保留 means no automatic urging until the owner instructs a restart; 合図待ち is a separate marker, not a state.

## Untagged watcher (VERIFIED for commit dfb077b; non-root permissions untested)
Use [付け忘れ検出係の初心者向け説明](docs/explain/untagged-watch.md). Make clear that the first run learns existing files without alerting; subsequent new unregistered files may produce pending. Watched roots are read-only, yet the local state directory is written. Explain pending, manual ack, repeated output with a stable ID, and lack of delivery guarantee. A script MUST NOT claim that stdout by itself guarantees exactly-once delivery, or that a SHA-256 integrity digest prevents deliberate tampering. Do not claim scheduler, inbox, tagging or deletion features exist.

## Shared Intake (VERIFIED for d9b24aa; Linux/root tested only)
Use [共通受け皿を初心者へ説明する](docs/explain/shared-intake.md). Explain why one inbox prevents fragmented monitoring, why append-only journals are authoritative but flag.json is rebuildable, what "saved" means (journal fsync followed by derived flag update), what the four statuses mean, and why an acquisition error is not the same as zero new items. Mention that 90-day terminal-item review is only a dry-run preview; actual deletion, external delivery, scheduling and AI judgment are not included. A new assistant must NOT claim at-most-once delivery beyond persistent local idempotent ingestion, or assure compatibility with private systems.

The reported C-7 clean-room explanation test passed for commit d9b24aa. Emphasize that this is a **revision- and environment-scoped** validation and that derived flag repair is not equivalent to repairing a corrupted authoritative JSONL journal. Unprocessed/audited entries are never included in retention-preview; 90 days is not permission to delete.

## Injection-size watcher (VERIFIED for a60df96, Linux/root scope)
Use [投入量見張り係を説明する](docs/explain/injection-size-watch.md). Explain exact file bytes vs model-specific tokens, previous-measurement delta vs derived weekly rate with at least seven days of history, and why incomplete readings have **no valid total**. The operator makes private dated backup/draft packages only upon warning, **not applied edits**. Plain Markdown/text drafts stay unchanged; JSON may lose only insignificant out-of-string whitespace, with a measured byte comparison. Its A–F labels are **public generalized placeholders**, not known private meanings; it cannot automatically prove that a reduced draft preserves human-relevant key points. Semantic self-test status is NOT_ASSESSABLE. V.E.S.T.A.R.D. reported fresh-Muse C-7 explanation PASS for exact-byte sizes, UNKNOWN token counts, no source auto-application, generalized A–F labels, and NOT_ASSESSABLE semantic reconstruction. Do not claim the 10%-equality CLI boundary or non-root/other OS behaviors were independently reproduced.

## Organizer (VERIFIED for 84ca9fe in reported Linux/root scope)
Explain in natural Japanese: **「整理」=ファイル寿命の候補判定であり、フォルダ分けではない**; tags are declared by the file creator when creating the file; the public CLI reads only membership records and mtime, not file content; it does not search for a separate authoritative copy or infer missing tags; permanent is excluded; unknown/missing is held or an error. A file at 14 days is a proposal for review, **not moved**. The internal trash and later purge are **not present in public code**, and the shared-intake 90-day retention mechanism is a different independent concern. A human decides high-impact actions. No claimed verified benefits, no actual user file use, and do not treat output as approval.

The reported independent C-7 explanation passed on all five requirements: lifetime rather than folder sorting, creator-declared tags, tag+mtime without authoritative-copy checks, proposal-only public code, and distinct 14-day / private 1-month / shared-intake 90-day rules. Its exact text was kept in the tester's private records, not independently reread by E.L.I.S. Non-root and other OS behavior remains UNVERIFIED.

## Deadline reminder (VERIFIED for deae596; independent C-7 reported PASS)
Explain in plain Japanese: **発動と配送は別**. A fired timer is not delivery, and delivery is not evidence the human read anything. Registered deadlines carry UTC, IANA-local-with-offset, and integer epoch seconds: mismatches FAIL CLOSED. A reminder fires only once. If the derived outbox is missing, the valid append-only journal can rebuild it without another firing. The CLI never dispatches to shared intake, never configures cron, and never calculates human intent. The local `ack` merely records externally **claimed** receipt data (no cryptographic confirmation, `consumer_verified=false`). Errors are not converted to an empty/no-due status; identical consecutive check failures form one open incident, later recurrence a distinct episode. The separate single-shot cron-based business deadline system is reference-only and not implemented. Include explicit autonomy/authority limits and private-data warnings in C-7.

V.E.S.T.A.R.D. reported the fresh-Muse C-7 explanation satisfied all four core points: firing is distinct from delivery, delivery from human reading, errors from zero results, and manual receipt assertions from verified acceptance. The private explanation transcript was not inspected by E.L.I.S. No actual sender, recipient verification or scheduler exists in this public code.

## History cleaner (VERIFIED for 61c3364, C-7 reported PASS)
In simple Japanese distinguish **受け皿のレコード** from filesystem files or Git histories. Only `reported/discarded` at least 90 days from the **terminal** time are age candidates. `unprocessed` and `audited` are NEVER candidates. A reminder's item body may meet the age test but its state events remain protected; errors, dedupe seen and any prune audit must not be discarded. Public Shared Intake v1 lacks separate seen retention and `prepare/complete`, so age candidate is NOT deletion authorization and `safe_to_delete_count=0` for every report. Pending/partial failures (`hold`, exit 2) and corrupted journal/config (`error`, exit 1) are not interpreted as zero candidates. `--source-roles` is a local human declaration, not verified provenance. Explain what is unimplemented: `--apply`, seq renumbering, deletion, checkpoints, cron. P4 and separate P5 owner approval remain open.

V.E.S.T.A.R.D. reported the fresh-Muse C-7 explanation passed the five required points: Shared Intake *records*, not filesystem/Git files; no candidates from unprocessed/audited; `candidate` does not permit deletion; errors/seen/reminder state events/prune records are protected; public code contains no deletion implementation. The full tester transcript was not reread by E.L.I.S. Independent synthetic CLI proof is not proof of actual safe record deletion.
