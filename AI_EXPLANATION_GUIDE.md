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
