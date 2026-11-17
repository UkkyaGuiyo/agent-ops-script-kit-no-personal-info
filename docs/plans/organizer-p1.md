# 第6号P1調査：整理係 / Organizer

**Status:** PLANNED — generalized P1 inventory requested only. No public implementation, scheduling, real file operations or release authorized.  
**Decision source:** E.L.I.S. EVP/1 `20261117-022`; operator catalog in `SPEC_P0.md` states: "**Propose safe file categorization**".

## Why this next

With five operators independently VERIFIED within tested scopes, choose a **proposal-only** organizer before the potentially destructive history cleaner/retention manager. The aim is to validate observations, classification, explanation and human approvals **without moving or deleting any files**. This is a production priority recommendation, **not** a claim about the actual private implementation.

## V.E.S.T.A.R.D. P1 inventory (generalized facts, no private data)

1. **Purpose:** What recurring manual problem is the real organizer intended to solve? Is it a file tree, task list, Notion records or something else? Do not assume filesystem organization if different.
2. **Inputs and scope:** What exact types, allowed directories, relative paths, known schemas and explicit exclusions are used? Which operations are out of scope?
3. **Classification taxonomy:** What categories and priority rules exist; what can be determined mechanically, and what requires semantic judgment? How are conflicts, unknown and ambiguous items represented?
4. **Evidence for a proposal:** Which metadata (name, type, size in B, dates with timezone, tags, extensions, directory depth, duplicate fingerprints) are actually inspected? Are contents read? Distinguish confirmed from inferred.
5. **Output contract:** What is returned to a human or AI: source alias, proposed destination/category, rule ID, reason/evidence, confidence if measurable, veto flags, and a reversible plan? How is a proposed plan distinguished from an executed change?
6. **Safety boundary:** Can the real internal tool move, rename, copy, tag, overwrite, delete, send or edit anything? Which actions need explicit owner approval? The **first public pilot must only produce proposals**.
7. **Conflicts and identity:** How are duplicate names/paths, case-folding, symlink traversal, nested roots, cyclic links and races handled? Does a stable snapshot/file ID matter? Avoid guessing.
8. **Errors and recovery:** Handling of missing/inaccessible inputs, invalid schema, concurrent changes, partial scan, unreadable folders, unsafe destination, incomplete outputs and stale state. Failure must not be misreported as an empty/clean collection.
9. **State, cadence and dependencies:** Is there durable history, proposal IDs, pending/ack, scheduled runs, existing shared-intake link, or a user interface? Report NONE or UNKNOWN precisely; do not infer integration from other operator existence.
10. **Synthetic tests and explanation:** Misleading filenames, mixed extensions, nested paths, symlink escapes, duplicates, ambiguous classification, protected paths, missing input, collision, large tree, and zero-change dry-run. Fresh Muse must explain **"提案は実行ではない"**, human approval, uncertainty and exactly what inputs are read.

## Deliverables

- Existing internal **actual facts vs intended design vs UNKNOWN** table (no inflated "implemented" claims).
- Generalized input/output JSON schemas with typed fields, units and statuses.
- Category/rule ordering, ambiguity handling and explicit action/authority matrix.
- Failure/retry/identity contract and synthetic test matrix.
- Source of any baseline/threshold or scheduling requirements and unresolved design questions.

**Security:** Transfer no private source code, file names, real paths, screenshots, account IDs, logs, personal data, credentials or client information. Never change the actual private organizer, data, automations or public repository during P1. E.L.I.S. reviews the reported contract first and independently implements a synthetic public PILOT only after the design gate. Any future write/move stage must be separately designed, audited and owner-approved.

**No work is authorized** on history cleaning, retention deletion, external delivery, or a formal tagged release by this P1 order.
