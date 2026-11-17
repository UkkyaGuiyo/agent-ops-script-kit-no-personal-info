#!/usr/bin/env python3
"""Read-only retention-age preview for the public Shared Intake JSONL v1.

This does NOT delete records, compact journals, re-sequence events, or attest
that any record is safe for deletion. No network access or scheduler.
Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Iterator

VERSION = 1
TERMINAL = frozenset({"reported", "discarded"})
STATES = frozenset({"unprocessed", "audited", "reported", "discarded"})
TRANSITIONS = {
    "unprocessed": frozenset({"audited", "discarded"}),
    "audited": frozenset({"reported", "discarded"}),
    "reported": frozenset(), "discarded": frozenset(),
}
ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
SOURCE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")
OUTCOMES = frozenset({"success", "partial", "error"})
# The public intake has no authoritative prepare/complete/prune_log protocol.
PRUNE_MARKERS = ("prune_log", "prune_log.json", "prune-log.json", "prune-prepare.json")

class PreviewError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code

class PreviewHold(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreviewError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _bad_constant(_value: str) -> None:
    raise PreviewError("INVALID_NUMBER")


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes,
                          parse_constant=_bad_constant)
    except PreviewError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise PreviewError("INVALID_JSON") from exc


def _instant(value: Any) -> dt.datetime:
    if not isinstance(value, str):
        raise PreviewError("BAD_TIME")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("missing offset")
        return parsed.astimezone(dt.timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise PreviewError("BAD_TIME") from exc


def _id(value: Any, pattern: re.Pattern[str] = ID) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise PreviewError("BAD_ID")
    return value


def _secure_path(path: Path, *, directory: bool, missing_code: str) -> Path:
    path = Path(os.path.abspath(path))
    for node in reversed((path, *path.parents)):
        try:
            mode = node.lstat().st_mode
        except FileNotFoundError as exc:
            raise PreviewError(missing_code) from exc
        except OSError as exc:
            raise PreviewError("UNREADABLE_PATH") from exc
        if stat.S_ISLNK(mode):
            raise PreviewError("SYMLINK_PATH")
    mode = path.lstat().st_mode
    if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
        raise PreviewError("UNEXPECTED_PATH_TYPE")
    return path


def _locked_read(root: Path) -> Iterator[None]:
    # Same lock inode as scripts/shared_intake.py. Never create it.
    path = root / ".intake.lock"
    if not path.exists() and not path.is_symlink():
        raise PreviewHold("MISSING_INTAKE_LOCK")
    _secure_path(path, directory=False, missing_code="MISSING_INTAKE_LOCK")
    try:
        fd = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise PreviewError("LOCK_UNREADABLE") from exc
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise PreviewHold("LOCK_BUSY") from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise PreviewHold("LOCK_BUSY") from exc
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

_locked_read = contextlib.contextmanager(_locked_read)


def load_policy(path: Path) -> dict[str, str]:
    path = _secure_path(path, directory=False, missing_code="MISSING_POLICY")
    try:
        policy = strict_json(path.read_bytes())
    except OSError as exc:
        raise PreviewError("POLICY_UNREADABLE") from exc
    if not isinstance(policy, dict) or set(policy) != {"version", "source_roles"} or type(policy["version"]) is not int or policy["version"] != 1:
        raise PreviewError("BAD_POLICY_SCHEMA")
    roles = policy["source_roles"]
    if not isinstance(roles, dict):
        raise PreviewError("BAD_POLICY_SCHEMA")
    for source, role in roles.items():
        _id(source, SOURCE)
        if role not in ("general", "reminder") or not isinstance(role, str):
            raise PreviewError("BAD_SOURCE_ROLE")
    return roles


def read_journal(root: Path) -> list[dict[str, Any]]:
    for marker in PRUNE_MARKERS:
        if (root / marker).exists() or (root / marker).is_symlink():
            raise PreviewHold("UNSUPPORTED_PRUNE_EVIDENCE")
    for entry in ("flag.json", "state.json"):
        file = root / entry
        if file.exists() or file.is_symlink():
            _secure_path(file, directory=False, missing_code="UNREADABLE_DERIVED")
    for entry in root.iterdir():
        if entry.name.startswith(".intake-temp-"):
            raise PreviewHold("INTERRUPTED_INTAKE_SAVE")
    events = _secure_path(root / "events", directory=True, missing_code="MISSING_JOURNAL")
    try:
        files = sorted(events.iterdir())
    except OSError as exc:
        raise PreviewError("UNREADABLE_JOURNAL") from exc
    if not files:
        raise PreviewHold("EMPTY_JOURNAL_NO_BASELINE")
    result: list[dict[str, Any]] = []
    for path in files:
        if not DAY.fullmatch(path.name):
            raise PreviewError("UNEXPECTED_JOURNAL_ENTRY")
        _secure_path(path, directory=False, missing_code="MISSING_JOURNAL_FILE")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PreviewError("UNREADABLE_JOURNAL") from exc
        if not raw or not raw.endswith(b"\n"):
            raise PreviewError("PARTIAL_JOURNAL")
        for line in raw.splitlines():
            if not line:
                raise PreviewError("EMPTY_JOURNAL_LINE")
            record = strict_json(line)
            if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != VERSION:
                raise PreviewError("BAD_JOURNAL_SCHEMA")
            instant = _instant(record.get("occurred_at"))
            if instant.date().isoformat() + ".jsonl" != path.name:
                raise PreviewError("EVENT_DAY_MISMATCH")
            result.append(record)
    return result


def replay(events: list[dict[str, Any]]) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    seen_ids: set[str] = set()
    source_pairs: set[tuple[str, str]] = set()
    runs: dict[tuple[str, str], dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for idx, event in enumerate(events, start=1):
        if type(event.get("seq")) is not int or event["seq"] != idx:
            raise PreviewError("BAD_SEQ")
        eid = _id(event.get("event_id"))
        if eid in seen_ids:
            raise PreviewError("DUPLICATE_EVENT_ID")
        seen_ids.add(eid)
        kind = event.get("kind")
        if kind == "item_added":
            item = event.get("item")
            if not isinstance(item, dict) or type(item.get("schema_version")) is not int or item["schema_version"] != 1:
                raise PreviewError("BAD_ITEM")
            ident = _id(item.get("item_id"))
            where = item.get("where")
            if not isinstance(where, dict):
                raise PreviewError("BAD_ITEM_SOURCE")
            source = _id(where.get("source_id"), SOURCE)
            _instant(item.get("when_fetched"))
            if item.get("status") != "unprocessed":
                raise PreviewError("BAD_INITIAL_STATE")
            if ident in items:
                raise PreviewError("DUPLICATE_ITEM_ID")
            source_event = item.get("source_event_id")
            if source_event is not None:
                pair = (source, _id(source_event))
                if pair in source_pairs:
                    raise PreviewError("DUPLICATE_SOURCE_EVENT")
                source_pairs.add(pair)
            items[ident] = {"state": "unprocessed", "terminal_at": None, "source": source,
                            "event_ids": [eid], "has_source_event_id": source_event is not None}
        elif kind == "item_transition":
            ident = _id(event.get("item_id"))
            old, new = event.get("from_state"), event.get("to_state")
            if ident not in items or items[ident]["state"] != old or new not in TRANSITIONS.get(old, ()):
                raise PreviewError("BAD_TRANSITION")
            item = items[ident]
            item["state"] = new
            item["event_ids"].append(eid)
            if new in TERMINAL:
                item["terminal_at"] = _instant(event["occurred_at"])
        elif kind == "source_run_started":
            pair = (_id(event.get("source_id"), SOURCE), _id(event.get("run_id")))
            if pair in runs:
                raise PreviewError("DUPLICATE_RUN")
            runs[pair] = {"state": "RUNNING", "has_error": False, "event_ids": [eid]}
        elif kind == "source_run_error":
            pair = (_id(event.get("source_id"), SOURCE), _id(event.get("run_id")))
            _id(event.get("error_code"))
            if pair not in runs or runs[pair]["state"] != "RUNNING":
                raise PreviewError("BAD_RUN_ERROR")
            runs[pair]["has_error"] = True
            runs[pair]["event_ids"].append(eid)
            errors.append({"event_id": eid, "reason": "ERROR_AUDIT_PROTECTED"})
        elif kind == "source_run_completed":
            pair = (_id(event.get("source_id"), SOURCE), _id(event.get("run_id")))
            if pair not in runs or runs[pair]["state"] != "RUNNING" or event.get("outcome") not in OUTCOMES:
                raise PreviewError("BAD_RUN_COMPLETION")
            runs[pair]["state"] = "COMPLETED"
            runs[pair]["event_ids"].append(eid)
        else:
            # Public Shared Intake v1 has no prepare/complete/prune kind.
            raise PreviewError("UNSUPPORTED_EVENT_KIND")
    return {"items": items, "runs": runs, "errors": errors, "event_count": len(events)}


def preview(root: Path, roles: dict[str, str], *, days: int, as_of: dt.datetime) -> dict[str, Any]:
    if type(days) is not int or not 0 <= days <= 36500:
        raise PreviewError("BAD_RETENTION_DAYS")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise PreviewError("BAD_AS_OF")
    now = as_of.astimezone(dt.timezone.utc)
    root = _secure_path(root, directory=True, missing_code="MISSING_DATA_DIR")
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or checkout in root.parents:
        raise PreviewError("DATA_DIR_IN_PUBLIC_CHECKOUT")
    with _locked_read(root):
        events = read_journal(root)
        state = replay(events)
    items = []
    counts = {"candidate": 0, "not_due": 0, "excluded": 0, "hold": 0}
    for ident, item in sorted(state["items"].items()):
        age_seconds = None
        if item["state"] not in TERMINAL:
            decision, reason = "excluded", "NONTERMINAL_NEVER_PRUNE"
        else:
            elapsed = now - item["terminal_at"]
            age_seconds = elapsed.total_seconds()
            if elapsed < dt.timedelta(0):
                decision, reason = "hold", "FUTURE_TERMINAL_TIMESTAMP"
            elif elapsed < dt.timedelta(days=days):
                decision, reason = "not_due", "TERMINAL_BELOW_RETENTION"
            elif item["source"] not in roles:
                decision, reason = "hold", "UNKNOWN_ITEM_ORIGIN"
            else:
                decision, reason = "candidate", "TERMINAL_AT_OR_BEYOND_RETENTION"
        counts[decision] += 1
        declared_role = roles.get(item["source"], "UNKNOWN")
        items.append({"item_id": ident, "state": item["state"], "decision": decision,
                      "reason": reason, "source_role_declared": declared_role,
                      "origin_verified_independently": False,
                      "age_seconds": round(age_seconds, 6) if age_seconds is not None else None,
                      "event_ids_protected": item["event_ids"], "event_delete_allowed": False,
                      "seen_retention_independent": False, "deletion_safe": False})
    runs = []
    for (source, run_id), run in sorted(state["runs"].items()):
        if run["has_error"]:
            decision, reason = "hold", "ERROR_AUDIT_PROTECTED"
        elif run["state"] == "RUNNING":
            decision, reason = "excluded", "RUN_NOT_COMPLETED"
        else:
            decision, reason = "hold", "RUN_RETENTION_RULE_UNCONFIRMED"
        runs.append({"source_id": source, "run_id": run_id, "state": run["state"],
                     "decision": decision, "reason": reason,
                     "event_ids_protected": run["event_ids"], "deletion_safe": False})
    held_count = counts["hold"] + sum(x["decision"] == "hold" for x in runs)
    return {"status": "hold" if held_count else "preview", "schema_version": 1,
            "as_of_utc": now.isoformat(timespec="seconds"), "retention_days": days,
            "cutoff_inclusive": True, "counts": counts,
            "record_count": state["event_count"], "run_count": len(runs), "run_held_count": sum(x["decision"] == "hold" for x in runs),
            "item_previews": items, "run_previews": runs,
            "protected_error_event_count": len(state["errors"]),
            "seen_memory_independent": False,
            "prune_prepare_complete_verified": False,
            "journal_compaction_authorized": False,
            "dry_run": True, "records_changed": 0,
            "safe_to_delete_count": 0,
            "external_integrity_proven": False,
            "notes": ["CANDIDATE_MEANS_AGE_ELIGIBLE_ONLY",
                      "PUBLIC_INTAKE_V1_HAS_NO_STANDALONE_SEEN_OR_PRUNE_LOG",
                      "REMINDER_STATE_EVENTS_PROTECTED",
                      "ERROR_EVENTS_PROTECTED"]}


def _hold(code: str, days: int) -> dict[str, Any]:
    return {"status": "hold", "reason": code, "retention_days": days,
            "item_previews": None, "counts": None, "dry_run": True,
            "safe_to_delete_count": 0, "records_changed": 0}


def _error(code: str) -> dict[str, Any]:
    return {"status": "error", "reason": code, "item_previews": None,
            "counts": None, "dry_run": True, "safe_to_delete_count": 0, "records_changed": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shared Intake v1 record retention-age preview ONLY. Never deletes.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Existing private intake directory")
    parser.add_argument("--source-roles", type=Path, required=True, help="Existing JSON declaration; never public with real IDs")
    parser.add_argument("--days", type=int, default=90, help="Configured retention age in days (default 90)")
    parser.add_argument("--as-of", help="ISO-8601 date with timezone; synthetic tests only")
    args = parser.parse_args(argv)
    try:
        when = _instant(args.as_of) if args.as_of is not None else dt.datetime.now(dt.timezone.utc)
        roles = load_policy(args.source_roles)
        result = preview(args.data_dir, roles, days=args.days, as_of=when)
        code = 2 if result["status"] == "hold" else 0
    except PreviewHold as exc:
        result, code = _hold(exc.code, args.days), 2
    except PreviewError as exc:
        result, code = _error(exc.code), 1
    except (OSError, ValueError, OverflowError, TypeError) as exc:
        result, code = _error("UNEXPECTED_LOCAL_IO_OR_VALUE"), 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return code

if __name__ == "__main__":
    sys.exit(main())
