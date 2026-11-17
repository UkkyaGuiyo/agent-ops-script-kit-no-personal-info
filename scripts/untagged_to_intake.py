#!/usr/bin/env python3
"""Manual, offline adapter from untagged_watch pending JSON to shared-intake JSON.

Does NOT ingest the item or acknowledge the source. GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def convert(record: object, source_id: str = "untagged-watch") -> dict[str, object]:
    if not isinstance(record, dict) or record.get("status") != "pending" or record.get("delivery") != "unconfirmed":
        raise ValueError("Expected an unacknowledged pending watcher report")
    report = record.get("report")
    if not isinstance(report, dict):
        raise ValueError("Missing pending report")
    from shared_intake import valid_time, validate_id, SOURCE_ID
    when = valid_time(report.get("when_utc"))
    validate_id(source_id, "source_id", SOURCE_ID)
    event = validate_id(report.get("event_id"), "event_id")
    if type(report.get("count")) is not int or report["count"] < 1:
        raise ValueError("Invalid reported count")
    items = report.get("items")
    if not isinstance(items, list) or len(items) != report["count"]:
        raise ValueError("Reported item count mismatch")
    # Preserve only generalized fields. The user MUST keep this output private.
    return {
        "schema_version": 1,
        "when_fetched": when,
        "where": {"source_id": source_id},
        "source_event_id": event,
        "who": "untagged_watch",
        "what": "new_untagged_files",
        "why": "newly observed files have no retention record",
        "how": "manual conversion of the watcher's durable pending report",
        "payload": {"count": report["count"], "items": items},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert watcher pending JSON for local intake")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--source-id", default="untagged-watch")
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.file.read_text(encoding="utf-8"))
        converted = convert(raw, args.source_id)
    except (OSError, ValueError, UnicodeError, TypeError):
        print(json.dumps({"status": "error", "message": "Invalid pending input"}))
        return 1
    print(json.dumps(converted, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
