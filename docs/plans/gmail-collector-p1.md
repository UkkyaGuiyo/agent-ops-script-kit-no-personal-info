# 第10号 P1調査：Gmail収集係 / Gmail Collector

**Status:** PLANNED, **generalized P1 inventory only**.  
**Basis:** E.L.I.S. EVP/1 `20261117-041` selects this operator after nine scope-limited VERIFIED pilots.  
**P0 catalog target:** "**Authorized minimal-scope collector**". No specific Gmail search/filter, account access, collection format, downstream action or live source is assumed without evidence.

## Priority and authority
Investigate this operator before the final Retention manager because it can be prototyped with **offline synthetic email-like records**. Actual mailbox access is higher risk than fixture processing and is **not authorized by this work order**. Do not use a connected Gmail plugin, retrieve real messages or message metadata, create drafts, mark read, modify labels, send, delete or export anything. A public pilot, if later accepted, should begin with a read-only fixture adapter and local non-delivering candidate preview. This is a proposed safety boundary, not the established internal behavior.

## Questions to V.E.S.T.A.R.D. (P1)

1. **Actual objective and maturity:** What task does the existing internal Gmail collector perform, if it exists? Implemented/tested/shadow-run/PLANNED? Identify the owner-approved specification revision without disclosing private code.
2. **Input vs output:** Is Gmail an input source, an output destination or only a trigger? What is actually retrieved (message headers, snippets, bodies, attachments, labels, threads, search results)? Which data is definitely out of scope?
3. **Authorized selection:** How are accounts, folders/labels, exact query criteria, sender allowlists, date limits, subject/body fields and content exclusions specified? Is there a separately versioned condition source? Report UNKNOWN if absent.
4. **Identity and deduplication:** Which stable identifiers define a unique record: provider message ID, thread ID, RFC Message-ID, policy ID or attachment ID? What happens if a thread gains a new message, an email is moved between labels, or identical mail is returned twice?
5. **Completeness and time semantics:** How are pagination, cursor/history ID, source revision, timezone/UTC, search windows, retention timestamps, page limits and deleted/changed messages handled? Define successful empty results separately from incomplete/failed fetch.
6. **Untrusted content:** How is HTML, text, MIME, links, file names, Unicode, headers, spoofed sender data or instructions embedded in a message treated? What data is actually inspected, normalized, excluded or passed through? No model instructions from retrieved mail.
7. **Output / Shared Intake:** Does the private workflow persist a local candidate, submit Shared Intake v1, use an outbox, notify a human, or mark Gmail state? Which step is considered durable acceptance, and what proves it? Collector must not infer that a candidate was read/approved.
8. **Persistence / recovery:** Seen list, bootstrap, duplicate event IDs, pending delivery, retry/ack, atomicity, failure records and policy changes. How are failed scans prevented from advancing last-success state or misreporting zero?
9. **Error, permission and privacy:** Handle expired/revoked read scopes, missing label, partial API pages, rate limit, timeout, malformed MIME, attachment too large, schema drift, corrupt state and lock contention. Minimize personal data in logs/output. Identify any actions requiring separate human approval.
10. **Synthetic tests and C-7 explanation:** One-shot ID dedup, multiple messages in one thread, two threads with shared sender/subject, page truncation, changed labels, malformed dates, mixed text/HTML, adversarial instructions, incomplete bootstrap, retry after failure, and stable mapping to local Shared Intake v1 if relevant. Explain **"取得≠判定≠通知成功≠返信"** and precisely which Gmail actions did NOT happen.

## Deliverables
- FACT (verified internal behavior) vs confirmed design vs HYPOTHESIS vs UNKNOWN/UNVERIFIED, with source/version;
- Generalized input/output schemas including typed IDs, units, date and timezone semantics;
- Minimal Gmail permission matrix (read, metadata, label, mark-read, draft, send, delete); only established capabilities, no inferred access;
- Source completeness, cursor/dedup, pending/ack and recovery contract;
- Expected output when no messages, when partial/error, and when state is invalid;
- Synthetic test suite design, C-7 teaching points, and unresolved U1...Un for subsequent E.L.I.S. P1 adjudication.

## Explicit limits
P1 must not call Gmail, connect accounts, read user messages, download attachments, write to Notion, create schedules or submit real Shared Intake items. Do not relay real sender addresses, subject lines, message bodies, account IDs, paths, tokens, screenshots, customer data or actual logs. Do not alter private automations, AI bulletin board, task instructions, diary, existing public source or repository history. No live collector implementation or external-account permission is authorized by this work order. The repo remains PREVIEW; P4/P5 release gates separate.
