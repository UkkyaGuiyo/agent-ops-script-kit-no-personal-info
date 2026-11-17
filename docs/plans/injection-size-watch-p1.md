# 第5号のP1調査：投入量見張り係 / Injection-size watcher

**Status:** PLANNED / generalized P1 inventory requested. No implementation, scheduling, or file modification authorized yet.  
**Basis:** E.L.I.S. next-production decision in EVP/1 `20261117-020`; catalog in `SPEC_P0.md` calls for measuring files and **drafting, never applying, reductions**.

## Why this operator next

Choose a primarily **read-only** measuring tool before destructive history cleanup and connected-account collectors. This is a production-order decision, **not** a claim that the private script's real behavior has been examined. The name `injection-size` must not be interpreted as a prompt-injection/security scanner without evidence.

## P1 questions for V.E.S.T.A.R.D.

1. **What is measured?** Are these text blocks supplied to an AI, attached documents, prompt templates, Notion pages, or another category? Identify exact general purpose and out-of-scope content.
2. **Input scope:** Which file formats or source types are supported? Single files, directories, configurations, explicit allowlists? Are linked paths and inaccessible inputs rejected?
3. **Units:** Distinguish UTF-8 **bytes**, Unicode code points/characters, lines, and **tokens** (model-/tokenizer-specific). Identify which quantities are exact, estimated, or UNKNOWN.
4. **Thresholds and baseline:** Which limits are configured, what is compared, and when is an alert issued? Are there per-file, combined, or versioned thresholds?
5. **Reduction proposal:** Is the result a summary, a suggested diff, proposed truncation, or candidate list? Does the original ever get modified? This public pilot must **never automatically apply changes**.
6. **Sensitive content:** Can measurements be produced without storing or echoing actual text, private paths, credentials, client info or raw prompts? Specify sanitized output requirements and redaction policy.
7. **State and duplicates:** Is there any persistent snapshot, event ID, delivery or acknowledgment? If absent, explicitly report NONE. Do not invent shared-intake coupling.
8. **Failure handling:** Reading failures, encoding errors, unsupported formats, partial scans, very large files, memory/time limits, symlinks and filesystem changes. ERROR/UNKNOWN must not become zero length.
9. **Environment:** Python/version/OS dependencies, whether it works entirely offline, model tokenization dependencies, and any known performance observations with **units**.
10. **Tests and explanation:** Purely synthetic normal, threshold, multilingual/emoji, empty, malformed, inaccessible, huge and mixed-input cases. Fresh Muse must explain that an estimated token count is not an exact universal token count, and that no input is rewritten without explicit owner approval.

## Deliverables / submission contract

Provide a generalized P1 behavioral specification; input/output schemas with types and units; measurable vs estimated vs unknown distinctions; synthetic test matrix; authority boundary; failure cases; outstanding UNKNOWNs. Internal code, real user files and real paths, operational prompts, account/customer data and logs are **not** to be transferred.

Once P1 is reconciled with the actual internal operator, E.L.I.S. may independently implement a public PILOT and V.E.S.T.A.R.D. may independently verify. Formal P5 RELEASED remains a separate owner decision.
