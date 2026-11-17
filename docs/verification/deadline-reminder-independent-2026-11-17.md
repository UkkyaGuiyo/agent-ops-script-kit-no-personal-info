# 第7号 期限リマインダー係：独立検証概要（EVP/1 20261117-031）

**Date:** 2026-11-17 (JST)  
**Code commit:** `deae5969af6ab358e700b9e8e3b68f159bc032b2`  
**Verdict:** E.L.I.S. `ACCEPT_WITH_CONDITIONS`; PILOT → VERIFIED, revision- and environment-scoped.  
**Source:** V.E.S.T.A.R.D. fresh-clone independent test report. Full private logs and fresh-Muse text were not transmitted or inspected by E.L.I.S. E.L.I.S. separately checked the public source, tests and contract.

| Criterion | Reported observation | Assessment |
|---|---|---|
| Clone identity | HEAD `deae596` matches exact commit | PASS (reported) |
| Complete suite | **303/303 PASS** (prior 223 + deadline 80) | PASS (reported) |
| Registration | Same payload yields stable ID, retry `added=false` | PASS (reported) |
| Exactly one firing | At due -1 second: 0; at due: 1 and pending outbox 1; at due +1 second: new firing 0 | PASS (reported) |
| External sends | `NONE` throughout; public code does not have a sender | PASS for intended local-only contract |
| Three timestamp forms inconsistent | `TIME_MISMATCH` exit 1 | PASS (reported) |
| Cancelled reminder | Does not fire | PASS (reported) |
| Manual receipt assertion | `delivery_attested`, `consumer_verified=false` | PASS (reported), **not authenticated delivery proof** |
| Outbox reconstruction | `repair-outbox` restores same pending ID; no journal edits or duplicate firing | PASS (reported) |
| Malformed journal | `BAD_JOURNAL`, exit 1 (Fail Closed) | PASS (reported) |
| Timestamp without offset | `BAD_TIME`, exit 1 | PASS (reported) |
| C-7 explanation | Firing vs delivery vs human reading, errors not empty output, manual receipt unverified; additionally manual-only and no journal auto-repair | PASS (reported) |
| Shared Intake real connection | Not implemented or tested | OUT_OF_SCOPE |
| Non-root and other OSs | Not tested | UNVERIFIED |

## Limits
A local `fired` transition does not prove the consumer received anything. The derived `pending` outbox is a durable local obligation. The `ack` operation records an **external assertion**, does not authenticate the consumer, and always indicates `consumer_verified=false`. Neither `delivery_state=delivered` nor an outbox status demonstrates human reading.

The append-only `deadline-events.jsonl` is authoritative. A missing derived outbox can be rebuilt from a **valid journal**. Corrupted authoritative rows cannot be repaired by `repair-outbox` and must fail closed. No actual Shared Intake integration, network sending, cron installation, externally verified receipt, human-read tracking, 90-day absence rule or deletion exists in this pilot.

This is not independent proof of Linux non-root, Windows/macOS, NFS, alternate tzdb, workload scale or live user deployment. The whole kit remains **PREVIEW**; P4 security/license/history audit and separate owner P5 formal-release approval are unfulfilled.
