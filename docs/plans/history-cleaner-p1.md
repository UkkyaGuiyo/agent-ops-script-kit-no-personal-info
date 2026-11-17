# 第8号 P1調査：履歴掃除係 / History Cleaner

**Status:** PLANNED; generalized P1 inventory only.  
**Basis:** EVP/1 `20261117-031`, after seven operators reached scope-limited VERIFIED. P0 catalog says only: **"Show cleanup candidates with dry-run"**.

## Why this next
Prefer an observable, non-mutating candidate preview before any deletion or irreversible history rewriting. The term **history** is ambiguous: it may refer to file versions, append-only logs, archived tasks, Git history, backup history or something else. Do not assume. The internal implementation may have a different maturity or purpose; establish it from its own authoritative design and evidence. Do not confuse this operator with Organizer's declared `disposable` + mtime rule or Shared Intake's 90-day terminal-item preview.

## P1 questions to V.E.S.T.A.R.D.
1. **Actual identity and maturity:** What is the exact internal scope, authoritative specification revision, actual implementation stage and observed tests? Distinguish implemented versus design-only, UNVERIFIED and UNKNOWN.
2. **Input/source:** What constitutes a single history entry? Which formats and sources are read? What is the source of truth? What records, backups, logs, references and current entries must never be candidates?
3. **Eligibility:** Which confirmed fields support candidate selection (state, time, origin, reference identity, retention tag, archival status, etc.)? State exact thresholds/units/clock basis if present, or UNKNOWN. Do not borrow 14-day, one-month or 90-day rules from unrelated operators.
4. **Safety veto:** How are active, pending, legally or operationally retained, referenced, unaudited, incomplete or otherwise protected histories excluded? Can unknown reference integrity produce a HOLD rather than a candidate?
5. **Output:** Generalized preview JSON fields, typed IDs, reason codes, candidates, exclusions/holds, counts, byte sizes where actually measured, as-of time and evidence. What is never echoed because it is sensitive?
6. **Internal permissions:** Does the real cleaner merely preview or also quarantine, truncate, compact, move, delete, rewrite Git history or purge data? Exact phases and whose explicit approval is required. Public first PILOT is **dry-run-only**.
7. **Identity and concurrency:** Stable IDs, duplicates, restart behavior, append-only history, checksums/sequence gaps, race conditions, symlinks/unsafe paths and how a stale preview is recognized.
8. **Errors and recovery:** Fail Closed rules for missing/corrupt sources, partial reads, unknown orphans, inconsistent counts, unreachable dependencies, failed probes and interrupted operations. How is "UNKNOWN" distinguished from "safe to remove"?
9. **State/dependencies:** Persistent local state? Existing jobs, schedules, audit manifests and integrations (e.g., Shared Intake)? What is actually operational versus merely planned? Document NONE vs UNKNOWN.
10. **Synthetic testing and C-7:** Exact thresholds, active/pending protection, broken references, malformed logs, duplicate entries, unreadable sources and zero mutations to all inputs (SHA-256 and mtime). Fresh Muse must explain **"candidate is not deletion"**, no invented safety proof and human authority.

## Requested deliverables
- Generalized FACT/INFERENCE/UNKNOWN table with precise source/version evidence.
- Input/output JSON schema with types, units, permitted states, reason codes.
- Candidate/exclusion/HOLD decision table and explicit authority matrix.
- Recovery and idempotence contract, synthetic test matrix, C-7 explanation points.
- Unresolved U1/U2/... questions for E.L.I.S. prior to independent implementation.

## Boundaries
Do not transfer or publish private source, real histories, filenames, paths, IDs, logs, credentials, account/customer information, or any private metadata. Do not edit existing Notion records, private scripts, Git histories, scheduled jobs, or any live files. No cleanup may run from this P1 work order. Public code is separately reviewed after this P1; no scheduling, deletion, physical purge, irreversible operation or formal release authorized.
