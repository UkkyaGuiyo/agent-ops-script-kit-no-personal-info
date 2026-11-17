# 保持タグ付け忘れ検出係：技術仕様

**Status: PILOT. Independent environment and fresh-Muse explanation tests PENDING.**
**License:** GPL-3.0-only. Independent public implementation; no private source code copied.

## Purpose and boundaries
Monitor **multiple configured, nonoverlapping local root directories**. Scan regular file metadata, compare root-relative paths with the root's retention-record JSON and locally persisted `seen` state. Report **only newly observed untagged paths**, not all old untagged files. It does not inspect ordinary file contents, assign tags, decide retention classes, move/delete files, use external services or schedule work.

## Input schema
`config` JSON: `{"version":1,"roots":[{"name":"synthetic-root","path":"...","exclude_subtrees":[]}]}`.
- Root `name`: unique ASCII identifier, 1–48 characters: letters, numbers, hyphen, underscore.
- Root `path`: existing directory (absolute or relative to config file), no symlink in ancestors. Overlapping roots are refused.
- `exclude_subtrees`: optional list of root-relative forward-slash paths. Absolute paths, backslashes, `..` and empty components are rejected.
- Built-in excluded directory names: `.git`, `node_modules`, `__pycache__`, `venv`, `.venv`, `.trash`.
- A record file **must** exist at each root: `.retention_records.json`. It contains `{"entries":[{"path":"sub/example.txt","class":"disposable"}]}`. Optional top-level `version` is accepted **only** when it equals integer `1`. Any nonempty `class` value establishes registration; unknown values belong to the record owner's HOLD handling and are not deletion permission.
- Root-relative record paths cannot escape with `..`, absolute paths, backslashes or empty components. Duplicate paths are fatal input errors.
- Only regular files enter the observed set. The record file itself, symlinks, special files and excluded directories are not counted.

## State and delivery
`--state-dir` must identify an **already existing directory outside both this checkout and all watched roots**. Local state is written to `untagged-watch-state.json`; a lock file prevents concurrent operations. The state envelope contains `payload` and SHA-256 of canonical JSON `payload`, with `version=1`, `baseline_complete=true`, configuration fingerprint, `seen` and optional `pending`.

- SHA-256 detects accidental changes when the digest is not also replaced. It is **not** authentication or proof that the state is trustworthy against a malicious editor.
- Atomic state replacement uses an fsync'd temporary file and `os.replace`. Any orphaned `.state-temp-` file is treated as interrupted save, requiring manual inspection. State is **never silently recreated** after a detected failure.
- New installation: no saved state → baseline the current complete file set → no report.
- Existing installation: compute `new_untagged = (current_untagged_paths − previous_seen_paths)`; no report → save current seen atomically.
- If new untagged files exist, save a `pending` event (including `next_seen`) **before** showing its JSON. Re-running `scan` with pending replays the same event ID without rescanning.
- After **durable** acceptance by a separate consumer or explicit human handling, `ack --event-id ID` commits `next_seen` and clears pending. `ack` has no knowledge of downstream receipt; using it too early can lose a notification.
- A crash after a consumer accepted a report but before `ack` can cause **repeated output**, so the receiver MUST deduplicate by `event_id`. Exactly-once delivery is **not promised**. No actual external delivery is included.

## Output and return codes
`scan` JSON statuses: `baseline`, `ok`, `pending`, `locked`, `error`. `ack` returns `acknowledged` when successful. `pending` has `delivery=unconfirmed` and a report with `event_id`, `when_utc`, `where`, `who`, `what`, `why`, `how`, `count`, `items[{root,relative_path}]`. Counts are **files**; timestamp is ISO-8601 UTC. Do not publish reports: relative paths may be private data.

- **0:** success (includes baseline, normal scan, pending/replay and acknowledgment)
- **3:** lock conflict, current run skipped
- **1:** configuration, I/O, integrity, state or acknowledgment error; no normal result

## Limits and failure cases
Filesystem changes during a scan may affect what is observed. Path identity is root-relative path, not inode or content hash: delete/recreate at the same path may not be considered new. A new file that appears after a report becomes pending is handled after that report is acknowledged. Records and state created by other versions are not automatically migrated. An unknown class is treated as registered/hold, not as missing. The implementation has no automatic lock recovery, retention deletion, scheduler, or intake delivery.

[HowTo](../howto/untagged-watch.md) · [Explain to a beginner](../explain/untagged-watch.md) · [P1 decision](../plans/untagged-watch-p1.md).
