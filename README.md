# Agent Ops Script Kit | 個人情報流入禁止！！

> **個人情報流入禁止！！ / NO PERSONAL INFORMATION.** Never commit personal data, credentials, private operational records, private prompts, private paths, real account IDs, or customer data. Use synthetic examples only.

**Status: PREVIEW. Not a finished product.** A beginner-friendly collection of small, auditable script helpers. Scripts check repeatable facts, AI assistants explain the results, and humans approve consequential actions. Not affiliated with any AI company.

## Start here
- [初心者向けスタート](START_HERE_JA.md)
- [P0確定設計・公開範囲](SPEC_P0.md)
- [安全方針](SECURITY.md) / [サポート方針](SUPPORT.md)
- [AI向け導入](AI_SETUP_GUIDE.md) / [AI向け説明](AI_EXPLANATION_GUIDE.md)
- [容量見張り係の説明](docs/explain/capacity-watch.md)

## Current pilot: capacity watcher
Requires **Python 3.10+**; no account, network, scheduling, file deletion, or write access. It sums apparent sizes of ordinary files in configured folders; it does **not** measure disk free space or physical disk allocation.

```bash
python -m unittest discover -s tests -v
python scripts/capacity_watch.py --config config/examples/capacity-watch.example.json
```

The sample uses a synthetic directory. Keep any configuration with real paths **outside this repository**. Failed scans are errors, not zero-byte results. Independent verification was [reported and recorded](docs/verification/capacity-watch-2026-11-17.md) for commit e573312; the full kit remains PREVIEW, not RELEASED.

Other operators are **PLANNED**, not included as functioning code. See [SPEC_P0.md](SPEC_P0.md).

**License:** GPL-3.0-only ([LICENSE](LICENSE)); license obligations apply when distributing covered modified versions. Private modifications alone do not have to be published.
**Support:** no guaranteed ongoing personal assistance. See [SUPPORT.md](SUPPORT.md).

Every branch, PR, and commit in this repository is public. Nothing may be pushed until inspected for private information.
