# 第10号 Gmail収集係：独立検証概要（EVP/1 20261117-045）

**Date:** 2026-11-17 JST
**Tested code commit:** cbfa915930096a535bb229188f54a830d9b208ba
**Verdict:** ACCEPT_WITH_CONDITIONS: PILOT → VERIFIED only within Linux/root synthetic offline scope.
**Provenance:** Independent measurements reported by V.E.S.T.A.R.D. after a fresh clone. E.L.I.S. reread public source/spec/tests; the private full test logs and C-7 explanation were not supplied or independently run by E.L.I.S.

| Criterion | Reported observation | Result |
| --- | --- | --- |
| Clone identity | HEAD matches cbfa915930096a535bb229188f54a830d9b208ba | PASS (reported) |
| Whole project tests | **539/539 PASS; 0 SKIP** (prior 441 + new 98) | PASS (reported) |
| Shared Intake schema | Previously skipped validate_item compatibility test executed in new clone | PASS (reported) |
| Initial synthetic check | 11 messages across 2 fictional accounts: 8 candidates, 1 excluded, 2 unmatched, 8 pending | PASS (reported) |
| Identical recheck | 0 new candidates, 8 pending | PASS (reported) |
| Valid empty fixture | status=ok, 0 new, exit 0, distinct from fetch failure | PASS (reported) |
| Fixture byte integrity | SHA-256 identical before and after | PASS (reported) |
| External actions | gmail_connection=NONE; shared_intake_write=false | PASS for intentional nonfeatures |
| C-7 | 7/7 explained: offline-only, classification not final decision, error/partial/zero distinct, account+message ID, no execution or attachment opening, pending not delivered, private false-negative unresolved | PASS (reported) |
| Real importance accuracy | One direct important email was missed by internal system, root cause unresolved | UNRESOLVED |
| Non-root, other OS, actual Gmail and live intake | Not tested or not implemented | UNVERIFIED / OUT_OF_SCOPE |

## Decision limits
Public source has MailProvider protocol with only a local synthetic FixtureProvider. It cannot authenticate to or read Gmail, alter read/label state, fetch attachments, send/reply, submit Shared Intake ingest or schedule checks. A local candidate is a mechanical match, not evidence of true importance, delivery or human review. The synthetic suite gives no sensitivity/recall/false-negative-rate guarantee, and does not resolve the internal reported missed important email.

VERIFIED is scoped to this revision and reported Linux/root offline behavior. Full kit status stays PREVIEW; P4 security/license/history audit and explicit P5 human approval are still outstanding.
