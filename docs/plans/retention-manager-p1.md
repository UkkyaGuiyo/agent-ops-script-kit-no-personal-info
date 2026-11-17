# 第11号 P1調査：保持管理係 / Retention Manager

**Status:** PLANNED; P1 inventory only. **No implementation or cleanup authorized.**
**Basis:** EVP/1 20261117-045, the final of the eleven P0 operators.
**Only grounded P0 goal:** Recoverable staged cleanup. The actual private target and stages remain UNKNOWN pending source inspection by V.E.S.T.A.R.D.

## Distinction from existing operators
Organizer previews declared file lifetime based on tag + mtime; no move/delete. History Cleaner previews terminal Shared Intake record age with safe_to_delete_count=0; no record deletion. Do not assume Retention Manager is either of these, or automatically borrow 14-day, one-month or 90-day thresholds. Establish its real authoritative contract first.

## P1 investigation questions
1. **Actual scope and evidence:** exact source-of-truth specification/version, owner authorization, implementation status, real tests and production experience. What is managed: files, records, versions, snapshots, logs or other objects?
2. **Deletion unit and exclusions:** define identity, scope roots, permitted types, protected permanent data, active records, private task documents, dependencies and prohibited paths; UNKNOWN if not specified.
3. **Eligibility:** actual lifecycle metadata, tags, timestamps, retention units, expiry boundary, permanent and untagged treatment, and whose declaration is authoritative. Do not infer conditions from the name.
4. **Actual stages:** distinguish preview, staging, quarantine, trash, irreversible purge, restore, recovery. Which stages truly exist and which are only designed? What does recoverable mean operationally?
5. **Authority:** exact approvals and permissions per stage, manual apply flags if any, preconditions and independent human gates. Public P1 explicitly forbids performing any action.
6. **Identity and integrity:** stable IDs, original and staged path mapping, SHA-256/size, manifests, hardlinks, symlinks, mount boundaries, path collisions, stale previews, changed files and concurrent processes.
7. **Idempotency and interrupted runs:** implemented logs, state transitions, prepare/complete markers, checkpoints, replays, retry keys, rollback after partial failure and duplicate processing.
8. **Failure and restoration:** permission denied, corrupt/missing manifests, disk full, invalid path, partial moves, broken backups, unavailable evidence, interrupted restoration. Fail Closed; distinguish restored bytes from semantically correct restoration.
9. **Inter-operator responsibilities:** interaction with Organizer, Shared Intake, History Cleaner and other operators; retention intervals and timezones if actually present; actual automated scheduling and tested OS/filesystems.
10. **Synthetic test design and C-7:** exact expiry boundary if any, permanent/unknown protection, preview input SHA-256/mtime unchanged, symlink and path race attacks, interruption/retry, and byte-exact recovery using synthetic artifacts only. Fresh AI explains proposed candidate vs authorization, staged vs purged, and recovery limitations.

## Required generalized deliverables
Provide FACT / INFERENCE / HYPOTHESIS / UNKNOWN / UNVERIFIED with source revision and observation scope; input/output and manifest fields only if source-backed; units, reason/status/exit codes, stage transitions and authority matrix; recovery and idempotency rules; synthetic test matrix and C-7 criteria; unresolved U1 onward. Do not invent private thresholds or states.

## Public first-pilot proposal (not yet authorized)
Prefer read-only synthetic preview and a non-operational staging simulation until the exact private specification is audited. Whether a later public pilot will support reversible file moves is a **separate design and authorization decision**. No deletion, moving, copying, purge, restore against live data, backup modification, cron, Git rewriting or public release is permitted by this P1.

## Privacy and non-action
Send no private source, real filenames, paths, logs, manifests, credentials, customer data or personal details. Do not run or alter any private retention service, scheduled job, Git history, Notion page, AI board, task instruction or diary. P4 audit and P5 formal release approval are separate from P1.
