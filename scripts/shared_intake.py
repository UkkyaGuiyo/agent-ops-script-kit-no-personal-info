#!/usr/bin/env python3
"""Local, append-only shared intake. No network, scheduling or deletion.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

VERSION = 1
SOURCE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SIMPLE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
DAY_FILE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")
STATES = frozenset({"unprocessed", "audited", "reported", "discarded"})
TERMINAL = frozenset({"reported", "discarded"})
TRANSITIONS = {
    "unprocessed": frozenset({"audited", "discarded"}),
    "audited": frozenset({"reported", "discarded"}),
    "reported": frozenset(),
    "discarded": frozenset(),
}
OUTCOMES = frozenset({"success", "partial", "error"})


class IntakeError(Exception):
    """The operation could not be completed reliably."""


class LockUnavailable(IntakeError):
    """Another intake operation currently holds the lock."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def valid_time(value: object) -> str:
    if not isinstance(value, str):
        raise IntakeError("when_fetched must be an ISO-8601 timestamp with a timezone")
    try:
        when = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntakeError("Invalid ISO-8601 timestamp") from exc
    if when.tzinfo is None or when.utcoffset() is None:
        raise IntakeError("A timezone offset is required")
    return value


def timestamp(value: str) -> dt.datetime:
    valid_time(value)
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def validate_id(value: object, label: str, regex: re.Pattern[str] = SIMPLE_ID) -> str:
    if not isinstance(value, str) or not regex.fullmatch(value):
        raise IntakeError(f"Invalid {label}")
    return value


def item_identity(item: dict[str, Any]) -> str:
    source = item["where"]["source_id"]
    event = item.get("source_event_id")
    if event is not None:
        validate_id(event, "source_event_id")
    identifier = item.get("item_id")
    if identifier is not None:
        return validate_id(identifier, "item_id")
    if event is None:
        raise IntakeError("item_id or source_event_id is required")
    return "sha256-" + sha256([source, event])


def validate_item(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IntakeError("Item must be a JSON object")
    if raw.get("schema_version", VERSION) != VERSION or type(raw.get("schema_version", VERSION)) is not int:
        raise IntakeError("Unsupported item schema_version")
    if "when_fetched" not in raw:
        raise IntakeError("Missing when_fetched")
    valid_time(raw["when_fetched"])
    where = raw.get("where")
    if not isinstance(where, dict) or "source_id" not in where:
        raise IntakeError("Missing where.source_id")
    validate_id(where["source_id"], "where.source_id", SOURCE_ID)
    if "status" in raw and raw["status"] != "unprocessed":
        raise IntakeError("New items must begin as unprocessed")
    if "status" in raw and not isinstance(raw["status"], str):
        raise IntakeError("Invalid initial status")
    item = dict(raw)
    item["schema_version"] = VERSION
    item["status"] = "unprocessed"
    item["item_id"] = item_identity(item)
    try:
        canonical(item)
    except (TypeError, ValueError) as exc:
        raise IntakeError("Item is not JSON-serializable") from exc
    return item


def ensure_real_dir(folder: Path) -> Path:
    absolute = Path(os.path.abspath(folder))
    for node in reversed((absolute, *absolute.parents)):
        try:
            if stat.S_ISLNK(node.lstat().st_mode):
                raise IntakeError("Intake path must not traverse symlinks")
        except OSError as exc:
            raise IntakeError("Intake directory is inaccessible") from exc
    if not absolute.is_dir():
        raise IntakeError("Intake directory does not exist")
    checkout = Path(__file__).resolve().parents[1]
    if absolute == checkout or checkout in absolute.parents:
        raise IntakeError("Intake data must be stored outside the public checkout")
    return absolute


def ensure_regular(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    except OSError as exc:
        raise IntakeError("Unable to inspect data file") from exc
    if not stat.S_ISREG(mode):
        raise IntakeError("Data path must be a regular file, not a symlink")


def events_dir(root: Path, create: bool = False) -> Path:
    folder = root / "events"
    if create:
        try:
            folder.mkdir(mode=0o700, exist_ok=True)
        except OSError as exc:
            raise IntakeError("Cannot create journal directory") from exc
    try:
        mode = folder.lstat().st_mode
    except FileNotFoundError:
        if create:
            raise IntakeError("Journal directory missing after creation")
        return folder
    except OSError as exc:
        raise IntakeError("Cannot inspect journal directory") from exc
    if not stat.S_ISDIR(mode):
        raise IntakeError("Journal directory must be a real directory")
    return folder


class IntakeLock:
    """One persistent lock inode (POSIX flock or Windows msvcrt one-byte lock)."""

    def __init__(self, root: Path):
        self.path = root / ".intake.lock"
        self.handle: Any = None

    def __enter__(self) -> "IntakeLock":
        ensure_regular(self.path)
        try:
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
            self.handle = os.fdopen(fd, "r+b", buffering=0)
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                try:
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise LockUnavailable("Another intake operation holds the lock") from exc
            else:
                import fcntl
                try:
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise LockUnavailable("Another intake operation holds the lock") from exc
            return self
        except (OSError, LockUnavailable) as exc:
            if self.handle is not None:
                self.handle.close()
                self.handle = None
            if isinstance(exc, LockUnavailable):
                raise
            raise IntakeError("Unable to lock intake directory") from exc

    def __exit__(self, *_: object) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def atomic_json(path: Path, value: object) -> None:
    ensure_regular(path)
    temp_path: Path | None = None
    data = canonical(value) + b"\n"
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".intake-temp-", delete=False) as out:
            temp_path = Path(out.name)
            if os.name != "nt":
                os.fchmod(out.fileno(), 0o600)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp_path, path)
        temp_path = None
        if os.name != "nt":
            fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    except OSError as exc:
        raise IntakeError("Failed to update derived file") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def check_orphans(root: Path) -> None:
    try:
        if any(p.name.startswith(".intake-temp-") for p in root.iterdir()):
            raise IntakeError("Interrupted derived-file save; manual review required")
    except OSError as exc:
        raise IntakeError("Cannot inspect intake directory") from exc


def load_events(root: Path) -> list[dict[str, Any]]:
    folder = events_dir(root)
    if not folder.exists():
        return []
    output: list[dict[str, Any]] = []
    try:
        files = sorted(folder.iterdir())
    except OSError as exc:
        raise IntakeError("Cannot enumerate journals") from exc
    for file in files:
        if not DAY_FILE.fullmatch(file.name):
            raise IntakeError("Unexpected file in journal directory")
        ensure_regular(file)
        try:
            raw = file.read_bytes()
        except OSError as exc:
            raise IntakeError("Cannot read journal") from exc
        if raw and not raw.endswith(b"\n"):
            raise IntakeError("Incomplete journal line detected")
        for line in raw.splitlines():
            if not line:
                raise IntakeError("Empty journal line")
            try:
                record = json.loads(line.decode("utf-8"))
            except (ValueError, UnicodeError) as exc:
                raise IntakeError("Corrupted journal JSON") from exc
            if not isinstance(record, dict) or record.get("schema_version") != VERSION or type(record.get("schema_version")) is not int:
                raise IntakeError("Unsupported journal record")
            if not isinstance(record.get("occurred_at"), str) or timestamp(record["occurred_at"]).date().isoformat() + ".jsonl" != file.name:
                raise IntakeError("Journal event/date mismatch")
            output.append(record)
    return output


def replay(events: list[dict[str, Any]]) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    statuses: dict[str, str] = {}
    terminal_at: dict[str, str] = {}
    source_pairs: dict[tuple[str, str], str] = {}
    ids: dict[str, dict[str, Any]] = {}
    runs: dict[tuple[str, str], dict[str, Any]] = {}
    source_errors: list[dict[str, str]] = []
    last_seq = 0
    for rec in events:
        seq = rec.get("seq")
        if type(seq) is not int or seq != last_seq + 1:
            raise IntakeError("Noncontiguous journal sequence")
        last_seq = seq
        eid = validate_id(rec.get("event_id"), "journal event_id")
        if eid in ids:
            raise IntakeError("Duplicate journal event_id")
        ids[eid] = rec
        kind = rec.get("kind")
        if kind == "item_added":
            item = validate_item(rec.get("item"))
            identifier = item["item_id"]
            if identifier in items:
                raise IntakeError("Duplicate item ID in journal")
            pair_event = item.get("source_event_id")
            if pair_event is not None:
                pair = (item["where"]["source_id"], pair_event)
                if pair in source_pairs:
                    raise IntakeError("Duplicate source event in journal")
                source_pairs[pair] = identifier
            items[identifier] = item
            statuses[identifier] = "unprocessed"
        elif kind == "item_transition":
            item_id = validate_id(rec.get("item_id"), "item_id")
            before, after = rec.get("from_state"), rec.get("to_state")
            if item_id not in items or statuses[item_id] != before or after not in TRANSITIONS.get(before, ()):
                raise IntakeError("Illegal journal transition")
            statuses[item_id] = after
            if after in TERMINAL:
                terminal_at[item_id] = rec["occurred_at"]
        elif kind == "source_run_started":
            source_id = validate_id(rec.get("source_id"), "source_id", SOURCE_ID)
            run_id = validate_id(rec.get("run_id"), "run_id")
            pair = (source_id, run_id)
            if pair in runs:
                raise IntakeError("Duplicate source run")
            runs[pair] = {"source_id": source_id, "run_id": run_id, "status": "RUNNING", "outcome": None}
        elif kind == "source_run_error":
            source_id = validate_id(rec.get("source_id"), "source_id", SOURCE_ID)
            run_id = validate_id(rec.get("run_id"), "run_id")
            error_code = validate_id(rec.get("error_code"), "error_code")
            pair = (source_id, run_id)
            if pair not in runs or runs[pair]["status"] != "RUNNING":
                raise IntakeError("Source error without active RUNNING acquisition")
            source_errors.append({"source_id": source_id, "run_id": run_id,
                                  "error_code": error_code, "event_id": eid})
        elif kind == "source_run_completed":
            source_id = validate_id(rec.get("source_id"), "source_id", SOURCE_ID)
            run_id = validate_id(rec.get("run_id"), "run_id")
            pair = (source_id, run_id)
            if pair not in runs or runs[pair]["status"] != "RUNNING" or rec.get("outcome") not in OUTCOMES:
                raise IntakeError("Invalid source-run completion")
            runs[pair] = {"source_id": source_id, "run_id": run_id, "status": "COMPLETED", "outcome": rec["outcome"]}
        else:
            raise IntakeError("Unknown journal event kind")
    return {"items": items, "statuses": statuses, "terminal_at": terminal_at,
            "source_pairs": source_pairs, "event_ids": ids, "runs": runs,
            "source_errors": source_errors, "next_seq": last_seq + 1}


def flag_from(state: dict[str, Any]) -> dict[str, Any]:
    values = list(state["statuses"].values())
    unprocessed = values.count("unprocessed")
    audited = values.count("audited")
    return {"schema_version": VERSION, "raised": unprocessed > 0,
            "unprocessed_count": unprocessed, "open_count": unprocessed + audited,
            "total_items": len(values), "last_seq": state["next_seq"] - 1}


def summary_from(state: dict[str, Any]) -> dict[str, Any]:
    counts = {value: list(state["statuses"].values()).count(value) for value in sorted(STATES)}
    return {"schema_version": VERSION, "last_seq": state["next_seq"] - 1,
            "status_counts": counts, "flag": flag_from(state),
            "source_runs": sorted(state["runs"].values(), key=lambda x: (x["source_id"], x["run_id"])),
            "source_errors": state["source_errors"]}


def update_derived(root: Path, state: dict[str, Any]) -> None:
    # Fail closed if a previous atomic save crashed. Journal remains authoritative.
    check_orphans(root)
    atomic_json(root / "flag.json", flag_from(state))
    atomic_json(root / "state.json", summary_from(state))


def append_event(root: Path, rec: dict[str, Any]) -> None:
    folder = events_dir(root, create=True)
    path = folder / (timestamp(rec["occurred_at"]).date().isoformat() + ".jsonl")
    ensure_regular(path)
    encoded = canonical(rec) + b"\n"
    try:
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            amount = os.write(fd, encoded)
            if amount != len(encoded):
                raise IntakeError("Incomplete journal append; manual recovery required")
            os.fsync(fd)
        finally:
            os.close(fd)
        if os.name != "nt":
            dir_fd = os.open(folder, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except OSError as exc:
        raise IntakeError("Journal append failed; retry with same item ID") from exc


def read_authoritative(root: Path) -> dict[str, Any]:
    check_orphans(root)
    return replay(load_events(root))


def commit_event(root: Path, rec: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    enriched = {"schema_version": VERSION, "seq": old["next_seq"],
                "occurred_at": utc_now(), **rec}
    # Check the exact new event before an irreversible append.
    after = replay(load_events(root) + [enriched])
    append_event(root, enriched)
    update_derived(root, after)
    return after


def ingest(root: Path, raw: object) -> dict[str, Any]:
    item = validate_item(raw)
    identifier = item["item_id"]
    with IntakeLock(root):
        state = read_authoritative(root)
        pair_event = item.get("source_event_id")
        if pair_event is not None:
            pair = (item["where"]["source_id"], pair_event)
            if pair in state["source_pairs"] and state["source_pairs"][pair] != identifier:
                raise IntakeError("Conflicting item ID for source event")
        prior = state["items"].get(identifier)
        if prior is not None:
            if canonical(prior) != canonical(item):
                raise IntakeError("Conflicting payload for existing item_id")
            # Repair derived flag after a crash following a successful append.
            update_derived(root, state)
            return {"status": "accepted", "item_id": identifier, "added": False,
                    "current_state": state["statuses"][identifier], "flag": flag_from(state)}
        if pair_event is not None and pair in state["source_pairs"]:
            raise IntakeError("Duplicate source event with different ID")
        event_id = "add-" + sha256(["item_added", identifier])
        after = commit_event(root, {"event_id": event_id, "kind": "item_added", "item": item}, state)
        return {"status": "accepted", "item_id": identifier, "added": True,
                "current_state": "unprocessed", "flag": flag_from(after)}


def transition(root: Path, item_id: str, new_state: str, event_id: str) -> dict[str, Any]:
    validate_id(item_id, "item_id")
    validate_id(event_id, "event_id")
    if new_state not in STATES:
        raise IntakeError("Unknown target state")
    with IntakeLock(root):
        state = read_authoritative(root)
        previous = state["event_ids"].get(event_id)
        if previous is not None:
            if previous.get("kind") != "item_transition" or previous.get("item_id") != item_id or previous.get("to_state") != new_state:
                raise IntakeError("event_id reused with conflicting transition")
            update_derived(root, state)
            return {"status": "transitioned", "item_id": item_id, "new_state": new_state,
                    "changed": False, "flag": flag_from(state)}
        current = state["statuses"].get(item_id)
        if current is None or new_state not in TRANSITIONS[current]:
            raise IntakeError("Invalid transition or unknown item_id")
        after = commit_event(root, {"event_id": event_id, "kind": "item_transition",
                                    "item_id": item_id, "from_state": current, "to_state": new_state}, state)
        return {"status": "transitioned", "item_id": item_id, "new_state": new_state,
                "changed": True, "flag": flag_from(after)}


def run_start(root: Path, source_id: str, run_id: str) -> dict[str, Any]:
    validate_id(source_id, "source_id", SOURCE_ID)
    validate_id(run_id, "run_id")
    with IntakeLock(root):
        state = read_authoritative(root)
        pair = (source_id, run_id)
        if pair in state["runs"]:
            update_derived(root, state)
            return {"status": "source_run", "added": False, **state["runs"][pair]}
        eid = "run-" + sha256(["run_start", source_id, run_id])
        after = commit_event(root, {"event_id": eid, "kind": "source_run_started",
                                    "source_id": source_id, "run_id": run_id}, state)
        return {"status": "source_run", "added": True, **after["runs"][pair]}


def run_error(root: Path, source_id: str, run_id: str, error_id: str, error_code: str) -> dict[str, Any]:
    validate_id(source_id, "source_id", SOURCE_ID)
    validate_id(run_id, "run_id")
    validate_id(error_id, "error_id")
    validate_id(error_code, "error_code")
    eid = "err-" + sha256([source_id, run_id, error_id])
    with IntakeLock(root):
        state = read_authoritative(root)
        previous = state["event_ids"].get(eid)
        if previous is not None:
            if previous.get("kind") != "source_run_error" or previous.get("error_code") != error_code:
                raise IntakeError("Conflicting source error event")
            update_derived(root, state)
            return {"status": "source_error", "recorded": False, "event_id": eid}
        run = state["runs"].get((source_id, run_id))
        if run is None or run["status"] != "RUNNING":
            raise IntakeError("No active source run for error")
        commit_event(root, {"event_id": eid, "kind": "source_run_error", "source_id": source_id,
                            "run_id": run_id, "error_code": error_code}, state)
        return {"status": "source_error", "recorded": True, "event_id": eid}


def run_finish(root: Path, source_id: str, run_id: str, outcome: str) -> dict[str, Any]:
    validate_id(source_id, "source_id", SOURCE_ID)
    validate_id(run_id, "run_id")
    if outcome not in OUTCOMES:
        raise IntakeError("Unknown run outcome")
    with IntakeLock(root):
        state = read_authoritative(root)
        pair = (source_id, run_id)
        run = state["runs"].get(pair)
        if run is None:
            raise IntakeError("No matching RUNNING source run")
        if run["status"] == "COMPLETED":
            if run["outcome"] != outcome:
                raise IntakeError("Conflicting source run outcome")
            update_derived(root, state)
            return {"status": "source_run", "changed": False, **run}
        eid = "run-" + sha256(["run_finish", source_id, run_id])
        after = commit_event(root, {"event_id": eid, "kind": "source_run_completed",
                                    "source_id": source_id, "run_id": run_id, "outcome": outcome}, state)
        return {"status": "source_run", "changed": True, **after["runs"][pair]}


def status(root: Path) -> dict[str, Any]:
    with IntakeLock(root):
        state = read_authoritative(root)
        derived = summary_from(state)
        # A stale or corrupt checkpoint is never mistaken for the truth.
        mismatches: list[str] = []
        for filename, expected in (("flag.json", derived["flag"]), ("state.json", derived)):
            path = root / filename
            ensure_regular(path)
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                mismatches.append(filename + ":missing")
            except (OSError, ValueError, UnicodeError):
                mismatches.append(filename + ":unreadable_or_corrupt")
            else:
                if value != expected:
                    mismatches.append(filename + ":stale")
        return {"status": "ok", "authoritative": "append_only_journal", **derived,
                "derived_warnings": mismatches}


def rebuild(root: Path) -> dict[str, Any]:
    with IntakeLock(root):
        state = read_authoritative(root)
        update_derived(root, state)
        return {"status": "rebuilt", "flag": flag_from(state),
                "last_seq": state["next_seq"] - 1}


def retention_preview(root: Path, days: int) -> dict[str, Any]:
    if type(days) is not int or days < 0:
        raise IntakeError("Retention days must be a nonnegative integer")
    with IntakeLock(root):
        state = read_authoritative(root)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        candidates = sorted(identifier for identifier, state_name in state["statuses"].items()
                            if state_name in TERMINAL and timestamp(state["terminal_at"][identifier]) <= cutoff)
        # Deliberately no deletion, pruning, rewriting journal or creating evidence.
        return {"status": "preview", "retention_days": days,
                "eligible_count": len(candidates), "eligible_item_ids": candidates,
                "deleted": False, "unprocessed_or_audited_never_eligible": True}


def read_item_file(name: str) -> object:
    try:
        if name == "-":
            return json.load(sys.stdin)
        return json.loads(Path(name).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise IntakeError("Cannot read item JSON") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local append-only shared intake (preview)")
    parser.add_argument("--data-dir", type=Path, required=True, help="Existing directory outside checkout")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest_parser = sub.add_parser("ingest", help="Persist one item from a JSON file or stdin (-)")
    ingest_parser.add_argument("--file", required=True)
    trans = sub.add_parser("transition", help="Record an authorized state transition")
    trans.add_argument("--item-id", required=True)
    trans.add_argument("--to", required=True, choices=sorted(STATES))
    trans.add_argument("--event-id", required=True)
    start = sub.add_parser("run-start", help="Record source acquisition started")
    start.add_argument("--source-id", required=True)
    start.add_argument("--run-id", required=True)
    error = sub.add_parser("run-error", help="Append an error event to a RUNNING acquisition")
    error.add_argument("--source-id", required=True)
    error.add_argument("--run-id", required=True)
    error.add_argument("--error-id", required=True)
    error.add_argument("--error-code", required=True, help="Generic error category; no personal details")
    finish = sub.add_parser("run-finish", help="Record outcome; an error is not zero new items")
    finish.add_argument("--source-id", required=True)
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--outcome", required=True, choices=sorted(OUTCOMES))
    sub.add_parser("status", help="Replay authoritative events, detect stale summaries")
    sub.add_parser("rebuild", help="Recompute flag and state from authoritative journal")
    retention = sub.add_parser("retention-preview", help="Dry-run terminal-item eligibility only")
    retention.add_argument("--days", type=int, default=90)
    args = parser.parse_args(argv)
    try:
        root = ensure_real_dir(args.data_dir)
        if args.command == "ingest":
            result = ingest(root, read_item_file(args.file))
        elif args.command == "transition":
            result = transition(root, args.item_id, args.to, args.event_id)
        elif args.command == "run-start":
            result = run_start(root, args.source_id, args.run_id)
        elif args.command == "run-error":
            result = run_error(root, args.source_id, args.run_id, args.error_id, args.error_code)
        elif args.command == "run-finish":
            result = run_finish(root, args.source_id, args.run_id, args.outcome)
        elif args.command == "status":
            result = status(root)
        elif args.command == "rebuild":
            result = rebuild(root)
        else:
            result = retention_preview(root, args.days)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except LockUnavailable:
        print(json.dumps({"status": "locked", "message": "Intake lock is busy"}))
        return 3
    except IntakeError as exc:
        # Do not echo raw payloads, local paths, or sensitive file content.
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    except (OSError, ValueError, OverflowError) as exc:
        print(json.dumps({"status": "error", "message": "Unexpected local I/O or value error"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
