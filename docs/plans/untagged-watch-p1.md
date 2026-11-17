# P1確定：保持タグ付け忘れ検出係

**Status: P1 accepted / public implementation VERIFIED for commit dfb077b (non-root permission-denial UNVERIFIED).**
**Basis:** V.E.S.T.A.R.D. generalized internal-spec report EVP/1 20261117-017. Private source, actual paths and operational data were not examined or copied.

## What this operator actually does
It checks newly observed **regular files** within configured local roots against a root-local JSON list of path-to-class records and a persisted `seen` snapshot. First scan establishes a silent baseline. Only a first-observed file absent from the record is eligible for a new report. It never assigns a tag, reads file bodies, moves files or deletes anything.

## U1–U3 decision (E.L.I.S.)
- **U1:** Retain durable `seen` + SHA-256 integrity envelope + `pending`. Use **one atomic state file**, not separate baseline and seen files. Abandoned write temporary files cause an error and require human inspection; no silent rebaseline.
- **U2:** Public pilot offers **CLI JSON stdout and an explicit `ack` step**. It has **no Gmail/Notion/intake integration, no scheduler, and no automatic outbound delivery**. stdout does not prove receipt. Pending replays keep the same event ID. A consumer must deduplicate by event ID; exactly-once external delivery is **not guaranteed**.
- **U3:** Public format uses one root-local `.retention_records.json` with an `entries` array of `path` (root-relative POSIX-style) and `class`. A record with either `disposable` or `permanent` means “tagged.” A nonempty unknown class is also **treated as registered/hold**, not deletion permission. Malformed entries, duplicate/escaping paths and unsupported schema versions fail closed.

## Explicitly different from private environment
Internal six-hour cadence is documentary context only. Public version is **manual**. Public `pending` is a local durable queue with manual acknowledgment, **not** an already implemented shared intake. Do not claim compatibility with the private state layout or delivery contract.

## Required safety
- State directory is writable but **outside monitored roots and this public checkout**. Watched roots stay read-only.
- No following symlinks. Exclude known artifact/build directories and user-listed relative subtrees.
- I/O, record parsing, state integrity and configuration drift errors stop without reporting “no new files.”
- Lock contention exits 3. Stale locks are a manual inspection task, not auto-removed.
- All files and generated JSON are potentially sensitive; only synthetic fixtures are publishable.

[Technical contract](../operators/untagged-watch.md) · [HowTo](../howto/untagged-watch.md) · [Beginner explanation](../explain/untagged-watch.md).
