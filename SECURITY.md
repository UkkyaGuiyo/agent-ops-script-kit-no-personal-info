# 個人情報流入禁止！！ / NO PERSONAL INFORMATION

**この公開リポジトリに個人情報を入れない。** Credentials, private logs, personal paths, real account IDs, e-mail addresses, customer data, security tokens, private prompts, screenshots, branch names and commit history containing private material are forbidden. Do not post secrets in Issues or PRs.

## Before every push
- Work from fresh, synthetic examples. Never turn an existing private repo public or import its history.
- Inspect staged content, generated files, filenames, git author metadata, diffs, and dependencies.
- Keep user configuration outside this repository, not merely hidden behind .gitignore.
- Public branches and PRs are PUBLIC. “Delete later” is not protection from history or clones.

## Runtime boundaries
- The capacity watcher and ledger checker inspect local inputs without changing them. The untagged watcher reads watched-root file metadata and root-local JSON records, **but writes a state JSON and lock into a separate user-provided directory outside the checkout and monitored roots**. No script follows symlinks, schedules work, or sends network data.
- Missing paths, invalid configs, interrupted state commits, malformed records and incomplete scans are errors. Never report partial data as complete. A pending report is not automatically delivered; manual ack is required after reliable acceptance. Runtime output and local state can reveal relative filenames and must not be posted publicly.
- Do not run with elevated privileges as a workaround.
- Future potentially destructive tools require explicit allowlists, dry-run, independent approval, safe staging, and recovery directions.

## Incident handling
If private information enters GitHub, immediately stop further publishing, assess exposure, rotate affected secrets, and plan proper history remediation. Deleting the current file does not erase history or external copies.

For a sensitive vulnerability, do not include private details in a public Issue. Use GitHub private vulnerability reporting if enabled; no guaranteed response channel is promised.

## Shared intake pilot
The shared intake writes a daily JSONL event journal, derived flag.json/state.json, and a persistent lock in a caller-owned **private data directory outside this repository**. Never commit the journal, derived files, original input items, or status output: they may contain private names, paths, source identifiers, and messages. The journal is authoritative and append-only; corrupted or partial records fail closed. A derived flag mismatch can be rebuilt from a valid journal. This pilot does **not** purge items or records; the 90-day option is only a preview. State transitions must be authorized externally. The manual untagged-watcher adapter must never auto-ack the producer.

## Injection-size watcher PILOT
This operator **reads UTF-8 source content** to measure bytes and to make optional private backups/drafts if a threshold is exceeded. It does not modify any source file. It **does write full source content to the user's private state directory** in dated backup packages after warning, so this directory must be outside the public checkout and protected like the source. Measurement history and draft JSON may contain sensitive content, size and fingerprints. Do not commit them. Paths containing symlinks are refused; unsupported, missing, corrupt, unscannable or oversized inputs cause explicit errors and an unknown total, never fake 0 B. A corrupt or incomplete history cannot auto-rebaseline; lock recovery requires inspection. SHA-256 and mechanical JSON round-trip checks do **not** prove meaningful semantic compression. No scheduling, external delivery, deletion or auto-application is implemented.

## Organizer (proposal-only PILOT)
This public script reads configured root-local `.retention_records.json` and obtains metadata with `lstat` for registered file paths only. It does not read registered file contents, crawl untagged files, create state, schedule jobs, alter tags, move to trash, rename, purge, delete, or access a network. Explicit exclusions protect `.trash` and common tool directories. Linked ancestors/inputs are rejected or held. Invalid records fail closed; per-entry unknown classes and missing registered paths produce **hold** rather than disposal authorization. Reports include **relative names and modification times** that may be private; do not publish actual output or source configuration. The 14-day example is not an automatic deletion authorization. An internal trash/purge process is outside this public pilot and must not be inferred from its docs.
