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
