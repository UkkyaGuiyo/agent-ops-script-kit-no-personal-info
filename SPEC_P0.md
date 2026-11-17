# P0 確定仕様書 | Agent Ops Script Kit
Version: 2026-11-17 / EVP 20261117-012, SUP1, 013.
Status: **design approved; capacity watcher VERIFIED for commit e573312; full release NOT approved**.

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
| History cleaner | Show cleanup candidates with dry-run | PLANNED |
| Organizer | Propose safe file categorization | PLANNED |
| Untagged watcher | Flag missing retention labels | PLANNED |
| Capacity watcher | Read-only local size scan with threshold | VERIFIED (e573312) |
| Gmail collector | Authorized minimal-scope collector | PLANNED |
| Notion jobs collector | Synthetic job intake examples | PLANNED |
| Retention manager | Recoverable staged cleanup | PLANNED |
| Injection-size watcher | Measure files and draft, never apply, reductions | PLANNED |
| Deadline reminder | Deadline notification and retry state | PLANNED |
| Shared intake | Preserve new, pending, failed, delivered | PLANNED |

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

## Open
Future operator dependencies; specific AI runtime and scheduling availability; exact release manifest and final approval.
