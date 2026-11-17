# 投入量見張り係：制作側ローカル検証

**Date:** 2026-11-17 (JST)  
**Status:** PILOT / independent verification PENDING  
**Producer's environment:** Linux, root (UID=0), Python 3.13.5. No live user files used.

## Evidence and test scope

- **52/52 PASS** using `python -m unittest discover -s tests -q` from an isolated synthetic build folder. The other operators' suites were not included in this local run.
- Scenarios: exact UTF-8 bytes and multilingual/emoji auxiliary counts; empty; combined file totals; size threshold below/equal/above; 7-day and daily measurement reference; derived weekly-rate normalization and decimal threshold; zero baseline; incomplete/unsupported/oversized/invalid/duplicate JSON; mocked unreadable input (not a non-root live test); symlinks; corrupt history or marker; interrupted draft; lock conflict; invalid config; draft/backup hash; JSON original lexeme preservation; no JSON-string whitespace mutation; no actual input replacement; no path/contents in stdout.
- **Anchors (synthetic fixtures):** example `status=ok`, exactly **249 B** total (120 B Markdown + 129 B JSON); warning example `status=warning`, original **129 B**, generated JSON draft **106 B**, saved **23 B**. All source fixture SHA-256 hashes were unchanged across these CLI runs. These numbers measure **test JSON whitespace removal only** and are not model-token savings.
- Python bytecode compilation completed successfully. The PII/secret pattern screen of new publicly proposed files found no matches. Hash/diff evidence indicates identity, not semantic correctness.

## Explicit limitations

- **Non-root permission-denial behavior was not observed.** Access refusal was simulated by a mocked exception. Windows/macOS, alternate Python versions, large real datasets, and long-duration runs were not independently checked.
- A fresh clone from the public GitHub target commit and complete historical project suite have not been tested by the producer. New code's status remains **PILOT** until the independent test-reporting AI separately checks the exact public commit and a context-free Muse can explain limitations.
- The source-side meaning reconstruction test is explicitly **NOT_ASSESSABLE**. A JSON whitespace-only proof or a verbatim text copy does **not** prove a useful human-readable compressed Markdown draft.
- Neither private operational files, private implementation, nor human content was used in code, tests, or synthetic fixtures.

## Release gate

Recheck from fresh public clone, run whole suite (prior independent count was 116, new tests 52; do not claim 168 until measured), verify anchor bytes and SHA-256, check no writes to monitored sources, new/old weekly baseline behavior, all error paths, package files and privacy, then perform a fresh Muse explanation. Independent VERIFIED still does not constitute owner-approved formal RELEASED.
