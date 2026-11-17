# AI setup guide: no prior context assumed

This document describes instructions to understand the kit, **not** authorization to act. Human instructions and actual tool permissions take precedence.

1. Read [START_HERE_JA.md](START_HERE_JA.md), [SECURITY.md](SECURITY.md), and [SPEC_P0.md](SPEC_P0.md).
2. Explain what the pilot does, its risks, and what the human controls. Do not imply that every operator is implemented.
3. Confirm local shell/filesystem access, Python 3.10+, and user permission. If unavailable, mark execution NOT VERIFIED and describe manual steps.
4. Run the unit tests and synthetic sample before using any user-selected directory.
5. Keep any real settings outside Git; never ask to post them or sensitive screenshots.
6. Understand that watcher outputs apparent file-size sums, not free disk space or actual allocated disk bytes.
7. If any scan fails, treat as ERROR/UNKNOWN; do not report “no files.”
8. Never set up scheduling, external accounts, or mutating behavior without separate user authorization.
9. Report exact tests, environment, known limits, and unknown results.

## Ledger checker (PILOT)
Read [ledger technical contract](docs/operators/ledger-check.md) and [ledger beginner explanation](docs/explain/ledger-check.md) before using. Run tests on synthetic inputs first. Never infer that a formatting check proves completion. Do not upload actual ledgers, paths, or local JSON output. The public checker is for a single Markdown file, not two-ledger comparison. Independent validation is pending.
