# P1調査依頼：保持タグの付け忘れ検出係
**STATUS: PLANNED. No implementation or scheduling authorized in this document.**
**Purpose:** Build a generic read-only checker that identifies items lacking a retention label. Start with an isolated synthetic dataset; do not copy any private script, manifest, or record.

## Why next
This operator is closer to the existing read-only pilots than cleanup, physical deletion, Gmail, or external-service intake. Its accurate behavior still depends on obtaining the original *generalized* retention tag contract. Do not assume the answer from its name.

## V.E.S.T.A.R.D. P1 questions
1. **Scope:** which roots and file types are considered, and which are excluded? What is the behavior for directories, symlinks, file removals during scan, and inaccessible paths?
2. **Source of truth:** where is the tag recorded (sidecar, ledger/manifest, file metadata, etc.) and how is that record correlated to each file? Do not supply private filenames or implementation.
3. **Vocabulary:** confirm whether allowed tags are `disposable` and `permanent` only; identify any metadata required in addition to the tag, e.g. timestamps, and malformed tag handling.
4. **Definitions:** what precisely counts as untagged vs unknown/unverifiable vs intentionally excluded? Does `false` mean absent, and how is failure represented?
5. **Inputs/outputs:** propose a sanitized schema with types, units, source of timestamp and explicit error statuses.
6. **Scheduling:** record the reported six-hour cadence as **context only**. Public v1 should remain manual by default; no cron/task changes without separate approval.
7. **Recovery:** show how a human can triage a false positive; this checker must not assign tags, move or delete files, modify metadata or send externally.
8. **Tests:** synthetic normal/untagged/malformed records, absent source, permission errors, duplicate entries, partial scan, symlinks, and failure not misreported as zero findings.
9. **Boundaries:** what behavior requires an AI or the owner? Never infer permission to delete from the existence of a tag.

## Next deliverable
Generalized, non-sensitive P1 report only. Mark unknown facts UNKNOWN. No private source, local paths, actual data, logs, personal information or credentials. E.L.I.S. will judge the specification before independently implementing a public PILOT.
