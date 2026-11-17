# 付け忘れ検出係：制作側ローカル試験の記録

**Date:** 2026-11-17
**Status:** PILOT / independent verification NOT YET PERFORMED
**Local test interpreter:** Python 3.13.5
**Source:** local synthetic fixture tests by the public design/audit AI. This document is NOT an independent verification report from the independent test-reporting AI.

## Results
- Tests in `tests/test_untagged_watch.py`: **33 / 33 PASS**, using `python -m unittest discover -s tests -q` on the isolated pilot directory.
- Covers first baseline, new untagged pending, repeated pending with stable event ID, explicit ack, newly created files while pending, registered disposable/permanent/unknown-hold labels, exclusions, record parsing, unknown schema, digest corruption, interrupted state write, lock conflict, symlink non-following, partial I/O failure, state outside checkout, multiple roots and CLI errors.
- No production filesystem, real record file, private path or external inbox was used.

## Transfer integrity
These refer to the exact source and test versions submitted to GitHub:
| Path | Bytes | SHA-256 |
|---|---:|---|
| `scripts/untagged_watch.py` | 18043 | `1584e64ea770f88e624d7d24a3efc48d8a3a58ae2a602009cd3d84f538129347` |
| `tests/test_untagged_watch.py` | 14491 | `da7a5f2dd2ce83bbd8f174718d6b8326515e355466bb7e9b425b42a34f439a49` |

SHA-256 establishes file identity only; it does not prove behavioral correctness. Git blobs are also separately inspected. A full release manifest and independent tester's raw results are still pending.

## Next gate
Fresh clone at the exact commit, synthetic 33/33 or full kit suite, first baseline, pending and ack lifecycle, state corruption refusal, no writes to watched roots, failure handling, and a clean-room Muse explanation. Do not mark VERIFIED before the independent report.
