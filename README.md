# Agent Ops Script Kit | 個人情報流入禁止！！

> **個人情報流入禁止！！ / NO PERSONAL INFORMATION.** Never commit personal data, credentials, private operational records, private prompts, private paths, real account IDs, or customer data. Use synthetic examples only.

**Status: PREVIEW. Not a finished product.** A beginner-friendly collection of small, auditable script helpers. Scripts check repeatable facts, AI assistants explain the results, and humans approve consequential actions. Not affiliated with any AI company.

## Start here
- [初心者向けスタート](START_HERE_JA.md)
- [P0確定設計・公開範囲](SPEC_P0.md)
- [安全方針](SECURITY.md) / [サポート方針](SUPPORT.md)
- [AI向け導入](AI_SETUP_GUIDE.md) / [AI向け説明](AI_EXPLANATION_GUIDE.md)
- [容量見張り係の説明](docs/explain/capacity-watch.md)

## Verified operator: capacity watcher
Requires **Python 3.10+**; no account, network, scheduling, file deletion, or write access. It sums apparent sizes of ordinary files in configured folders; it does **not** measure disk free space or physical disk allocation.

```bash
python -m unittest discover -s tests -v
python scripts/capacity_watch.py --config config/examples/capacity-watch.example.json
```

The sample uses a synthetic directory. Keep any configuration with real paths **outside this repository**. Failed scans are errors, not zero-byte results. Independent verification was [reported and recorded](docs/verification/capacity-watch-2026-11-17.md) for commit e573312; the full kit remains PREVIEW, not RELEASED.

**Ledger checker:** a second, read-only **VERIFIED** operator (scoped to commit 35f4d96) for a single Markdown task ledger. It checks the document's form, not whether work really happened. See [台帳係の導入](docs/howto/ledger-check.md), [初心者への説明](docs/explain/ledger-check.md), and [verification with limitations](docs/verification/ledger-check-2026-11-17.md).

**Verified with caveat: untagged watcher (commit dfb077b).** Read-only detection in monitored roots plus a writable, durable local state directory **outside this repository**. First run establishes a silent baseline. Later first-observed unregistered files become `pending` reports; `ack` is manual. **No external delivery, scheduler, tagging or deletion.** See [HowTo](docs/howto/untagged-watch.md), [beginner explanation](docs/explain/untagged-watch.md), and [technical limits](docs/operators/untagged-watch.md). Its [local test report](docs/verification/untagged-watch-local-2026-11-17.md) and [independent verification summary](docs/verification/untagged-watch-independent-2026-11-17.md) are published. Non-root permission-denial behavior is NOT independently verified. The full project remains PREVIEW.

**VERIFIED with limitations: Shared Intake / 共通受け皿 (commit d9b24aa).** A local collector that accepts JSON items from multiple producers, persists append-only daily JSONL event journals, maintains one derived unprocessed-count flag, and records state changes. It does **not** judge meaning, connect to services, auto-deliver, schedule work, or delete data. [Technical spec](docs/operators/shared-intake.md), [HowTo](docs/howto/shared-intake.md), [beginner explanation](docs/explain/shared-intake.md), [P1 decisions](docs/plans/shared-intake-p1.md), [local test report](docs/verification/shared-intake-local-2026-11-17.md) and [reported independent verification](docs/verification/shared-intake-independent-2026-11-17.md). Linux/root runtime was exercised; non-root, Windows and network filesystems remain UNVERIFIED. The kit remains PREVIEW, not RELEASED.

**VERIFIED within tested limits: Injection-size watcher / 投入量見張り係 (commit a60df96).** Measures explicit always-loaded AI context files in exact bytes, records measurements in a separate private directory and checks configured per-file size and seven-day-derived growth thresholds. Only upon a warning does it create **private dated backups and conservative draft proposals**, plus actual byte comparisons and mechanical self-tests. Markdown/text drafts remain byte-identical; JSON draft compaction only removes insignificant whitespace. **No source edits, no application, no model-token claim, no scheduler.** Semantic/key-point reconstruction is `NOT_ASSESSABLE`, not PASS. See [HowTo](docs/howto/injection-size-watch.md), [technical contract](docs/operators/injection-size-watch.md), [beginner explanation](docs/explain/injection-size-watch.md), [P1 decision](docs/plans/injection-size-watch-p1.md), [local test evidence](docs/verification/injection-size-watch-local-2026-11-17.md), [reported independent validation](docs/verification/injection-size-watch-independent-2026-11-17.md). Whole-kit 168/168 reported PASS under Linux/root; direct external CLI proof for the weekly-growth exact 10% boundary is still UNVERIFIED. Other OSs and non-root permissions UNVERIFIED.

**New PILOT: Organizer / 整理係.** Despite the name, this is **not** a folder sorter. It proposes tag-based **file lifetime** decisions using root-local `.retention_records.json` entries and each listed file's modification time. `disposable` + at least the configured duration (sample: 14 days) is a **candidate only**. `permanent` is never a candidate, and unregistered files are not examined. Missing, invalid, linked or unknown records are held or fail explicitly. The CLI never moves, writes, tags, trashes or purges anything. [Technical contract](docs/operators/organizer.md), [HowTo](docs/howto/organizer.md), [beginner explanation](docs/explain/organizer.md), [P1 decisions](docs/plans/organizer-p1.md), [local tests](docs/verification/organizer-local-2026-11-17.md).

Only the remaining planned operators lack working code. See [SPEC_P0.md](SPEC_P0.md).

**License:** GPL-3.0-only ([LICENSE](LICENSE)); license obligations apply when distributing covered modified versions. Private modifications alone do not have to be published.
**Support:** no guaranteed ongoing personal assistance. See [SUPPORT.md](SUPPORT.md).

Every branch, PR, and commit in this repository is public. Nothing may be pushed until inspected for private information.
