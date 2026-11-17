# P0 確定仕様書 | Agent Ops Script Kit
Version: 2026-11-17 / EVP 20261117-012, SUP1, 013.
Status: **design approved; nine operators VERIFIED (revision-scoped); full release NOT approved**.

## Mission
Publish an independently implemented, free GPL-3.0-only kit whose beginner users and initially uninformed AI assistants can (1) understand operators, (2) reproduce them where tools and permission allow, and (3) explain benefits, limitations, and risks in plain language.

**Separation:** script = deterministic observation and routine work; AI = bounded explanation and interpretation; human = consequential approvals. An AI reading this repository gains no new permissions.

## Non-negotiable boundaries
- **個人情報流入禁止！！** No personal data, credentials, private prompts, logs, account identifiers, customer information, real folder names, screenshots containing secrets, or private Git history.
- Existing private implementation must NOT be blindly copied or its repository made public. Create generalized new code with synthetic fixtures.
- Fail closed: a failed read is ERROR/UNKNOWN, not “no new events” or 0 bytes.
- Destructive or externally transmitting behavior is disabled by default; separately scoped authorization and recovery guidance are necessary.
- Do not claim AI compatibility, scheduled operation, performance gains, or real-world validation without evidence.
- Review all files, metadata, and diffs **before** any public push. Public feature branches and draft PRs are still public.
- Full release requires a later, explicit owner approval. Incremental public commits may proceed under the owner's build-in-public instruction after file-level safety review.

## Operator catalog
| Operator | Public target | Status |
|---|---|---|
| Ledger checker | Check one Markdown ledger's syntax without changing content | VERIFIED (35f4d96; non-root permissions untested) |
| History cleaner | Read-only Shared Intake v1 record-age candidates, never remove events/seen; no apply | VERIFIED (61c3364; Linux/root read-only scope) |
| Organizer | Preview tag-based file lifetime: disposable + mtime >= configured days, no move or purge | VERIFIED (84ca9fe; Linux/root scope) |
| Untagged watcher | First-observed unregistered regular files with durable local pending/ack | VERIFIED (dfb077b; non-root permissions untested) |
| Capacity watcher | Read-only local size scan with threshold | VERIFIED (e573312) |
| Gmail collector | Authorized minimal-scope collector | PLANNED |
| Notion jobs collector | Synthetic-only read adapter, one-time baseline, URL/day detection, local Shared Intake v1 proposals; no real Notion/send | VERIFIED (0eade24; Linux/root offline scope) |
| Retention manager | Recoverable staged cleanup | PLANNED |
| Injection-size watcher | Measure persistent AI context files in B and create private, conservative draft packages on warning; never apply | VERIFIED (a60df96; Linux/root, weekly CLI equality boundary untested) |
| Deadline reminder | One-shot UTC/IANA/epoch deadlines and durable local outbox; no external delivery | VERIFIED (deae596; Linux/root local scope) |
| Shared intake | Append-only local collector, transitions, derived flag, retry-safe IDs | VERIFIED (d9b24aa; Linux/root scope) |

PLANNED = not implemented; PILOT = synthetic local tests, independent environment validation pending; VERIFIED = independent validation recorded; RELEASED = human-approved tagged release.

## Documentation contract
For each operator: purpose, prerequisites, inputs/outputs and units, trigger, normal and failure paths, retries and duplicates, authority, dry-run, user explanation (what/why/benefits/risks/human choices), setup HowTo, safe stop/rollback, automated tests, independent verification status.

## Sequence
P0 public documentation → read-only capacity pilot → P1 per-operator private-source inventory → P2 independent generic implementation → P3 clean-room beginner and unknown-AI comprehension/reproduction test → P4 security/license/history/release audit → P5 explicit formal release approval.

## Roles
E.L.I.S. designs, authors and reviews. V.E.S.T.A.R.D. checks independent environment behavior and reports measured results. Owner controls priorities, license and formal release. Neither documentation nor a relay grants permissions.

## Evidence and limitations
The capacity watcher's independent validation summary is recorded in [docs/verification/capacity-watch-2026-11-17.md](docs/verification/capacity-watch-2026-11-17.md). This is a report of separate tester results, not the tester's raw logs. Status VERIFIED applies only to commit e573312a0a15ed359cc273d7001cf304c77e1bfc and its described runtime scope. Project remains PREVIEW and has no human-approved release.

## Ledger pilot / EVP 20261117-015
The ledger checker is a **single-file format verifier**, not a two-ledger comparator. Its contract is in [docs/operators/ledger-check.md](docs/operators/ledger-check.md). Independent validation was reported for [commit 35f4d96](docs/verification/ledger-check-2026-11-17.md) and is scoped as VERIFIED. The live non-root permission-denial behavior is NOT VERIFIED. The project remains PREVIEW.

## Untagged watcher / EVP 20261117-017
P1 documented; independent public implementation in [docs/operators/untagged-watch.md](docs/operators/untagged-watch.md). Decisions: retain hashed seen/pending, use manual local JSON output and explicit ack, publish a generalized root-local JSON retention-record format. No external intake, scheduler, automated tag assignment or deletion is included. Local synthetic tests passed; independently reported validation covers the state/pending/ack lifecycle and fresh-Muse explanation for [commit dfb077b](docs/verification/untagged-watch-independent-2026-11-17.md). Real non-root permission denial is UNVERIFIED. State hash is corruption detection, not cryptographic authentication. Formal release remains unapproved.

## Shared intake / EVP 20261117-019
The generalized P1 is accepted and independent public implementation is documented in [docs/operators/shared-intake.md](docs/operators/shared-intake.md). U1 daily append-only JSONL + derived flag/summary retained; U2 four fixed states; U3 90-day terminal-only **retention preview with no deletion**; U4 flag.json and status CLI, both derived from the journal. The manual [watcher adapter](scripts/untagged_to_intake.py) never auto-acks the producer. Local synthetic tests and [reported independent testing](docs/verification/shared-intake-independent-2026-11-17.md) covered the ingestion, duplicate, transition, derived-flag, corruption, source-failure and manual-adapter scenarios for commit d9b24aa. Linux/root environment only; non-root, Windows, long-running/performance, NFS and other filesystems are UNVERIFIED. Public code is revision-scoped VERIFIED; formal release is not approved.

## Injection-size watcher / EVP 20261117-021
The internal source was **an agreed design plus one manually completed procedure, not an implemented private automatic watcher**. [P1 inventory and decisions](docs/plans/injection-size-watch-p1.md) were accepted with conditions: configurable bytes/weekly thresholds; measurement + private backup/classification/draft/comparison/self-test; original files never auto-applied. Public A–F classification is a new generalization and **not the UNKNOWN private A–F mapping**. The [independent implementation](scripts/injection_size_watch.py) has [52 synthetic local PASS tests](docs/verification/injection-size-watch-local-2026-11-17.md); reported [independent fresh-clone validation](docs/verification/injection-size-watch-independent-2026-11-17.md) and C-7 explanation passed for a60df96 (168/168 whole-kit tests, including 52 watcher tests). The independently executed CLI weekly-growth equality boundary is UNVERIFIED; source uses Decimal and the local unit test covers exactly 10%. Linux/root tested; non-root and other OSs UNVERIFIED. Model tokens are UNKNOWN and semantic reconstruction is NOT_ASSESSABLE. Full kit remains PREVIEW and formal release unapproved.

## Organizer P1 / EVP 20261117-023
P1 established that the internal "Organizer" is a **retention lifetime manager**, not general file sorting. The internal design can move eligible disposable files into trash and separately purge old trash; this **public implementation deliberately omits both operations**. See [P1 decisions](docs/plans/organizer-p1.md), [proposal-only technical contract](docs/operators/organizer.md), [HowTo](docs/howto/organizer.md), [explanation](docs/explain/organizer.md), [local synthetic test evidence](docs/verification/organizer-local-2026-11-17.md). The public CLI only inspects preexisting records and mtimes for configured roots; an unregistered file is not inspected or tagged. Threshold example 14 days is configurable, while the private "1 month purge" and the shared-intake 90-day retention manager are **NOT public organizer functions**. The new operator has 55 local synthetic PASS tests; [independent fresh-clone validation](docs/verification/organizer-independent-2026-11-17.md) was reported as 223/223 whole-kit tests with CLI synthetic behavior and C-7 explanation PASS for commit 84ca9fe. Non-root and other OSs remain UNVERIFIED. Full release is NOT approved.

## Deadline reminder / EVP 20261117-030
The internal deadline reminder was reported as implemented and in operation; its one-shot deadline state and delivery/outbox are distinct. The [P1 decision](docs/plans/deadline-reminder-p1.md) selects **U1(a): local trigger and outbox only**, with a limited, **externally asserted and unverified** receipt-attestation CLI; U2: separate one-shot cron approach is **reference only**; U3: 5–15 minutes is an illustrative external scheduling interval, not code behavior. Public [pilot source](scripts/deadline_reminder.py) never sends, schedules, reads actual external inboxes or infers message reading. Its append-only event journal is authoritative; an outbox can be replayed after a crash; error episodes have a separate local record. UTC/local IANA/epoch seconds are verified as the same instant; one-time events never refire. **80 local synthetic tests PASS**, with [source and manifest evidence](docs/verification/deadline-reminder-local-2026-11-17.md). [Fresh-clone independent verification](docs/verification/deadline-reminder-independent-2026-11-17.md) was reported as **303/303 PASS** with synthetic CLI boundaries and C-7 explanation PASS at deae596. Real Shared Intake/consumer delivery is OUT OF SCOPE. Non-root, other OS, tzdb differences and prolonged operation remain UNVERIFIED. [Tech contract](docs/operators/deadline-reminder.md), [HowTo](docs/howto/deadline-reminder.md), [explanation](docs/explain/deadline-reminder.md). Entire kit is PREVIEW; owner-approved formal release remains unapproved.

## History cleaner / EVP 20261117-034
P1 established that the private History Cleaner is a **record-lifetime component of Shared Intake**, not a generic file cleanup or Git-history eraser. The independent [public source](scripts/history_cleaner.py) targets **Shared Intake public JSONL v1** and does **read-only** terminal-age preview, with default **90 days** from the final terminal transition. It never deletes rows, rewrites seq, creates prune evidence, copies private records or schedules work. An explicitly user-declared source-role map marks general versus reminder-derived items but is **not independently authenticated**; unknown origins are held. Reminder state events, error rows and deduplication memory are not deleted. Public v1 lacks independent `seen` retention and `prepare/complete` prune evidence; a `candidate` satisfies only the age criterion and **safe_to_delete_count is always 0**. Completed runs are held because their age rule is unknown. See [P1 decisions](docs/plans/history-cleaner-p1.md), [technical contract](docs/operators/history-cleaner.md), [HowTo](docs/howto/history-cleaner.md), [explanation](docs/explain/history-cleaner.md), [producer local evidence](docs/verification/history-cleaner-local-2026-11-17.md). Local testing had **66 PASS / 1 SKIP** (67 tests defined; skipped real intake integration absent from standalone build). **Fresh-clone independent test 370/370 PASS (reported)**, including the previously skipped true Shared Intake CLI integration test, and C-7 explanation PASS. See [independent verification](docs/verification/history-cleaner-independent-2026-11-17.md). Formal release still not authorized.

## Notion jobs collector / EVP 20261117-038
The internal operator was reported as **reading Notion source pages** and handing new date-page/new URL events to Shared Intake during daily shadow operation. Its live private implementation was **not copied**. Public [P1 decisions](docs/plans/notion-jobs-collector-p1.md) select **U1(b) read-only provider interface with offline FixtureProvider only**, **U2 strict versioned YAML subset and one-time persisted bootstrap with retry history**, **U3 local drafts shaped to Shared Intake v1, with NO actual ingest**. Detection compares existing date page IDs and page-local normalized URLs with query/fragment stripped; body text instructions never execute. Failed parent/schema/policy/state is ERROR, failed child is PARTIAL and unmarked for retry, never fictitious zero new jobs. A single atomic private state records seen and pending candidate items; policy SHA-256 appears on state/drafts. The example bootstrap has one old page/URL, first update produces three local candidate events, repeated update produces zero new events but three still pending. [Technical spec](docs/operators/notion-jobs-collector.md), [HowTo](docs/howto/notion-jobs-collector.md), [plain-language explanation](docs/explain/notion-jobs-collector.md), [local verification](docs/verification/notion-jobs-collector-local-2026-11-17.md). Producer local tests **70 PASS / 1 SKIP** (71 tests); the one skipped test requires the actual public Shared Intake module. **Fresh-clone independent validation 441/441 PASS (reported), no SKIP**, including the actual public Shared Intake v1 `validate_item` compatibility test; C-7 explanation also PASS as independently reported. See [P3 independent verification](docs/verification/notion-jobs-collector-independent-2026-11-17.md). Real Notion access, user job records, shared-intake delivery, application, scheduling and account changes are OUT OF SCOPE. The kit remains PREVIEW; owner-approved release is unapproved.

## Next P1 / Gmail collector
The next generalized inventory concerns the [Gmail collector](docs/plans/gmail-collector-p1.md), whose only P0-approved public target is **authorized minimal-scope collector**. Actual private behavior and schemas are **UNKNOWN** until reported. P1 does not authorize account connection, mailbox reads, writes, labels, sending, schedules, or real customer/message data. The preferred first public pilot, subject to P1 adjudication, is synthetic-only and local, with no real Gmail provider bundled. Retention manager remains PLANNED and separate.

## Open
Future operator dependencies; specific AI runtime and scheduling availability; exact release manifest and final approval.
