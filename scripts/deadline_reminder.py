#!/usr/bin/env python3
"""Local, non-network, append-only one-shot deadline/outbox pilot. GPL-3.0-only.

Reading these public scripts does not authorize scheduling or external delivery.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = 1
JOURNAL = "deadline-events.jsonl"
OUTBOX = "deadline-outbox.json"
FAILURES = "deadline-failures.json"
LOCKFILE = ".deadline-reminder.lock"
TEMP_PREFIX = ".deadline-temp-"
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
LOCAL_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:[+-]\d\d:\d\d)$")
UTC_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")


class ReminderError(Exception):
    def __init__(self, code: str, message: str = "Invalid or unavailable reminder state") -> None:
        self.code = code
        super().__init__(message)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated JSON key")
        result[key] = value
    return result


def reject_constant(_: str) -> None:
    raise ValueError("Nonfinite JSON number")


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates, parse_constant=reject_constant)
    except (ValueError, UnicodeError, TypeError, json.JSONDecodeError) as exc:
        raise ReminderError("BAD_JSON") from exc


def read_json(path: Path) -> Any:
    ensure_file_if_exists(path)
    try:
        return decode(path.read_bytes())
    except OSError as exc:
        raise ReminderError("READ_FAILED") from exc


def valid_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ReminderError("INVALID_ID", "Invalid " + label)
    return value


def exact_keys(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ReminderError("BAD_SCHEMA", "Unexpected " + label + " schema")
    return value


def parse_stamp(value: Any, *, utc: bool = False) -> dt.datetime:
    if not isinstance(value, str) or not (UTC_RE.fullmatch(value) if utc else LOCAL_RE.fullmatch(value)):
        raise ReminderError("BAD_TIME", "Datetime must use second precision with explicit offset")
    try:
        result = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReminderError("BAD_TIME") from exc
    if result.tzinfo is None or result.isoformat(timespec="seconds") != value:
        raise ReminderError("BAD_TIME")
    return result


def validate_due(raw: Any) -> dict[str, Any]:
    due = exact_keys(raw, {"utc", "local", "timezone", "epoch_seconds"}, "due")
    tz_name = due["timezone"]
    if not isinstance(tz_name, str) or not tz_name or len(tz_name) > 90:
        raise ReminderError("BAD_TIMEZONE")
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError) as exc:
        raise ReminderError("BAD_TIMEZONE") from exc
    utc = parse_stamp(due["utc"], utc=True)
    local = parse_stamp(due["local"])
    seconds = due["epoch_seconds"]
    if type(seconds) is not int or not 946684800 <= seconds <= 4102444799:
        raise ReminderError("BAD_EPOCH", "Epoch seconds must be a bounded integer")
    actual = EPOCH + dt.timedelta(seconds=seconds)
    if utc != actual or local.isoformat(timespec="seconds") != actual.astimezone(zone).isoformat(timespec="seconds"):
        raise ReminderError("TIME_MISMATCH", "UTC, IANA local and epoch seconds disagree")
    return due


def validate_item(raw: Any) -> dict[str, Any]:
    item = exact_keys(raw, {"schema_version", "origin_id", "condition_id", "due"}, "reminder")
    if type(item["schema_version"]) is not int or item["schema_version"] != VERSION:
        raise ReminderError("BAD_VERSION")
    origin = valid_id(item["origin_id"], "origin_id")
    condition = valid_id(item["condition_id"], "condition_id")
    due = validate_due(item["due"])
    return {"schema_version": VERSION, "origin_id": origin, "condition_id": condition, "due": due}


def item_id(item: dict[str, Any]) -> str:
    return "rem-" + digest([item["origin_id"], item["condition_id"], item["due"]["epoch_seconds"]])[:40]


def outbox_id(reminder_id: str) -> str:
    return "out-" + digest(["deadline-fired", reminder_id])[:40]


def check_path(path: Path, *, directory: bool) -> None:
    path = path.absolute()
    for node in reversed((path, *path.parents)):
        try:
            info = node.lstat()
        except FileNotFoundError as exc:
            raise ReminderError("MISSING_PATH") from exc
        except OSError as exc:
            raise ReminderError("PATH_ERROR") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ReminderError("SYMLINK_DISALLOWED")
        if node == path:
            if directory and not stat.S_ISDIR(info.st_mode):
                raise ReminderError("NOT_DIRECTORY")
            if not directory and not stat.S_ISREG(info.st_mode):
                raise ReminderError("NOT_REGULAR_FILE")
        elif not stat.S_ISDIR(info.st_mode):
            raise ReminderError("INVALID_PARENT")


def ensure_file_if_exists(path: Path) -> None:
    if path.is_symlink():
        raise ReminderError("SYMLINK_DISALLOWED")
    try:
        path.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ReminderError("PATH_ERROR") from exc
    check_path(path, directory=False)


def validate_root(root: Path) -> Path:
    root = root.absolute()
    check_path(root, directory=True)
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or checkout in root.parents:
        raise ReminderError("UNSAFE_STATE_DIR", "Private data must be outside public checkout")
    return root


def check_orphans(root: Path) -> None:
    try:
        for path in root.iterdir():
            if path.name.startswith(TEMP_PREFIX):
                raise ReminderError("INTERRUPTED_SAVE")
    except OSError as exc:
        raise ReminderError("STATE_SCAN_FAILED") from exc


class Lock:
    def __init__(self, root: Path):
        self.path = root / LOCKFILE
        self.fd: int | None = None

    def __enter__(self) -> "Lock":
        ensure_file_if_exists(self.path)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
            if os.name == "nt":
                import msvcrt
                os.lseek(self.fd, 0, os.SEEK_SET)
                if os.fstat(self.fd).st_size < 1:
                    os.write(self.fd, b"\0")
                os.lseek(self.fd, 0, os.SEEK_SET)
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except (OSError, BlockingIOError) as exc:
            if self.fd is not None:
                os.close(self.fd)
                self.fd = None
            raise ReminderError("LOCKED", "Another local reminder operation is active") from exc

    def __exit__(self, *_: object) -> None:
        if self.fd is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None


def sync_dir(path: Path) -> None:
    if os.name != "nt":
        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise ReminderError("SYNC_FAILED") from exc


def atomic_json(root: Path, name: str, value: Any) -> None:
    target = root / name
    ensure_file_if_exists(target)
    temp: Path | None = None
    try:
        fd, tmp = tempfile.mkstemp(dir=root, prefix=TEMP_PREFIX)
        temp = Path(tmp)
        with os.fdopen(fd, "wb") as file:
            file.write(canonical(value) + b"\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, target)
        temp = None
        sync_dir(root)
    except OSError as exc:
        raise ReminderError("SAVE_FAILED") from exc
    finally:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass


def empty_state() -> dict[str, Any]:
    return {"items": {}, "events": {}, "next_seq": 1, "outbox": {}}


def replay_event(state: dict[str, Any], event: Any) -> None:
    if not isinstance(event, dict) or not isinstance(event.get("kind"), str):
        raise ReminderError("BAD_JOURNAL", "Invalid event")
    kind = event["kind"]
    shape = {
        "registered": {"item"},
        "rescheduled": {"from_id", "item"},
        "cancelled": {"reminder_id"},
        "fired": {"reminder_id"},
        "delivery_attested": {"outbox_id", "receipt_id", "consumer_id"},
    }.get(kind)
    if shape is None or set(event) != {"version", "seq", "event_id", "at_utc", "kind"} | shape:
        raise ReminderError("BAD_JOURNAL")
    if type(event["version"]) is not int or event["version"] != VERSION:
        raise ReminderError("BAD_VERSION")
    if type(event["seq"]) is not int or event["seq"] != state["next_seq"]:
        raise ReminderError("BAD_SEQUENCE")
    eid = valid_id(event["event_id"], "event_id")
    if eid in state["events"]:
        raise ReminderError("DUPLICATE_EVENT")
    parse_stamp(event["at_utc"], utc=True)
    items = state["items"]
    if kind == "registered":
        item = validate_item(event["item"])
        rid = item_id(item)
        if event["event_id"] != "reg-" + rid[4:]:
            raise ReminderError("BAD_JOURNAL")
        if rid in items:
            raise ReminderError("DUPLICATE_ITEM")
        items[rid] = {"item": item, "status": "active", "rescheduled_to": None, "fired_at_utc": None}
    elif kind == "rescheduled":
        old = valid_id(event["from_id"], "from_id")
        item = validate_item(event["item"])
        rid = item_id(item)
        if event["event_id"] != "res-" + digest([old, rid])[:40]:
            raise ReminderError("BAD_JOURNAL")
        if old not in items or items[old]["status"] != "active" or rid in items:
            raise ReminderError("INVALID_TRANSITION")
        if item["origin_id"] != items[old]["item"]["origin_id"] or item["condition_id"] != items[old]["item"]["condition_id"]:
            raise ReminderError("INVALID_TRANSITION")
        items[old]["status"] = "cancelled"
        items[old]["rescheduled_to"] = rid
        items[rid] = {"item": item, "status": "active", "rescheduled_to": None, "fired_at_utc": None}
    elif kind == "cancelled":
        rid = valid_id(event["reminder_id"], "reminder_id")
        if event["event_id"] != "can-" + rid[4:] or rid not in items or items[rid]["status"] != "active":
            raise ReminderError("INVALID_TRANSITION")
        items[rid]["status"] = "cancelled"
    elif kind == "fired":
        rid = valid_id(event["reminder_id"], "reminder_id")
        if event["event_id"] != "fire-" + rid[4:] or rid not in items or items[rid]["status"] != "active":
            raise ReminderError("INVALID_TRANSITION")
        if parse_stamp(event["at_utc"], utc=True) < parse_stamp(items[rid]["item"]["due"]["utc"], utc=True):
            raise ReminderError("INVALID_TRANSITION")
        items[rid]["status"] = "fired"
        items[rid]["fired_at_utc"] = event["at_utc"]
        oid = outbox_id(rid)
        state["outbox"][oid] = {"outbox_id": oid, "reminder_id": rid, "delivery_state": "pending", "consumer_receipt_id": None,
                                 "fired_at_utc": event["at_utc"], "consumer_id": None}
    else:
        oid = valid_id(event["outbox_id"], "outbox_id")
        receipt = valid_id(event["receipt_id"], "receipt_id")
        consumer = valid_id(event["consumer_id"], "consumer_id")
        if event["event_id"] != "ack-" + digest([oid, receipt, consumer])[:40]:
            raise ReminderError("BAD_JOURNAL")
        if oid not in state["outbox"] or state["outbox"][oid]["delivery_state"] != "pending":
            raise ReminderError("INVALID_TRANSITION")
        state["outbox"][oid]["delivery_state"] = "delivered"
        state["outbox"][oid]["consumer_receipt_id"] = receipt
        state["outbox"][oid]["consumer_id"] = consumer
    state["events"][eid] = event
    state["next_seq"] += 1


def load_journal(root: Path) -> dict[str, Any]:
    path = root / JOURNAL
    ensure_file_if_exists(path)
    state = empty_state()
    if not path.exists():
        return state
    try:
        with path.open("rb") as file:
            for line in file:
                if not line.endswith(b"\n") or not line.strip() or len(line) > 40_000:
                    raise ReminderError("BAD_JOURNAL", "Invalid journal line")
                try:
                    replay_event(state, decode(line))
                except ReminderError as exc:
                    raise ReminderError("BAD_JOURNAL", "Invalid journal event") from exc
    except OSError as exc:
        raise ReminderError("READ_FAILED") from exc
    return state


def current_outbox(state: dict[str, Any]) -> dict[str, Any]:
    return {"version": VERSION, "last_seq": state["next_seq"] - 1,
            "entries": [state["outbox"][key] for key in sorted(state["outbox"])]}


def refresh_outbox(root: Path, state: dict[str, Any]) -> None:
    check_orphans(root)
    atomic_json(root, OUTBOX, current_outbox(state))


def append(root: Path, state: dict[str, Any], kind: str, when: dt.datetime, **payload: Any) -> None:
    record = {"version": VERSION, "seq": state["next_seq"], "event_id": payload.pop("event_id"),
              "at_utc": when.astimezone(dt.timezone.utc).isoformat(timespec="seconds"), "kind": kind, **payload}
    # Check the event is valid before making any persistent changes.
    shadow = {"items": {k: dict(v) for k, v in state["items"].items()}, "outbox": {k: dict(v) for k, v in state["outbox"].items()},
              "events": dict(state["events"]), "next_seq": state["next_seq"]}
    replay_event(shadow, record)
    path = root / JOURNAL
    ensure_file_if_exists(path)
    content = canonical(record) + b"\n"
    existed = path.exists()
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            count = os.write(fd, content)
            if count != len(content):
                raise ReminderError("SHORT_WRITE")
            os.fsync(fd)
        finally:
            os.close(fd)
        if not existed:
            sync_dir(root)
    except OSError as exc:
        raise ReminderError("WRITE_FAILED") from exc
    state.clear()
    state.update(shadow)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def write_failure(root: Path, code: str, when: dt.datetime) -> dict[str, Any]:
    path = root / FAILURES
    if path.exists():
        record = read_json(path)
        if (not isinstance(record, dict) or set(record) != {"version", "payload", "sha256"} or
                type(record["version"]) is not int or record["version"] != VERSION or
                not isinstance(record["sha256"], str) or digest(record["payload"]) != record["sha256"]):
            raise ReminderError("BAD_FAILURE_STATE")
        payload = record["payload"]
        if not isinstance(payload, dict) or set(payload) != {"occurrences", "open_code"} or not isinstance(payload["occurrences"], list):
            raise ReminderError("BAD_FAILURE_STATE")
        occurrences = payload["occurrences"]
        if payload["open_code"] is not None:
            if (not isinstance(payload["open_code"], str) or not occurrences or
                    not isinstance(occurrences[-1], dict) or
                    occurrences[-1].get("code") != payload["open_code"] or
                    occurrences[-1].get("resolved_at_utc") is not None):
                raise ReminderError("BAD_FAILURE_STATE")
        for occurrence in occurrences:
            if (not isinstance(occurrence, dict) or
                    set(occurrence) != {"occurrence_id", "code", "opened_at_utc", "resolved_at_utc"} or
                    not isinstance(occurrence["code"], str)):
                raise ReminderError("BAD_FAILURE_STATE")
    else:
        payload = {"open_code": None, "occurrences": []}
    if code != payload["open_code"]:
        if payload["open_code"] is not None:
            payload["occurrences"][-1]["resolved_at_utc"] = when.isoformat(timespec="seconds")
        if code:
            payload["occurrences"].append({"occurrence_id": "failure-" + digest([code,when.isoformat(), len(payload["occurrences"])])[:32],
                                            "code": code, "opened_at_utc": when.isoformat(timespec="seconds"), "resolved_at_utc": None})
        payload["open_code"] = code or None
        atomic_json(root, FAILURES, {"version": VERSION, "payload": payload, "sha256": digest(payload)})
    return payload


def run_check(root: Path, when: dt.datetime) -> dict[str, Any]:
    # The independent failure ledger remains writable even when this journal is corrupt.
    try:
        state = load_journal(root)
        check_orphans(root)
        fired = []
        for rid, row in sorted(state["items"].items()):
            if row["status"] == "active" and parse_stamp(row["item"]["due"]["utc"], utc=True) <= when:
                append(root, state, "fired", when, event_id="fire-" + rid[4:], reminder_id=rid)
                fired.append(rid)
        # The derived outbox is not authoritative. Each check reconciles all prior fired events.
        refresh_outbox(root, state)
        failure = write_failure(root, "", when)  # CLOSE previous failure episode after success.
        pending = [e for e in state["outbox"].values() if e["delivery_state"] == "pending"]
        return {"status": "ok", "new_fired_count": len(fired), "new_fired_ids": fired,
                "pending_delivery_count": len(pending), "pending_outbox_ids": sorted(x["outbox_id"] for x in pending),
                "delivery_attempts": 0, "external_delivery": "NONE", "last_seq": state["next_seq"] - 1,
                "open_failure_code": failure["open_code"]}
    except ReminderError as exc:
        # Error codes only. No sensitive arguments or tracebacks are written to failure ledger.
        try:
            write_failure(root, exc.code, when)
        except ReminderError:
            pass
        raise


def register(root: Path, raw: Any) -> dict[str, Any]:
    item = validate_item(raw)
    rid = item_id(item)
    state = load_journal(root)
    prior = state["items"].get(rid)
    if prior is not None:
        if prior["item"] != item:
            raise ReminderError("CONFLICTING_ITEM")
        refresh_outbox(root, state)
        return {"status": "registered", "reminder_id": rid, "added": False, "item_state": prior["status"]}
    append(root, state, "registered", now_utc(), event_id="reg-" + rid[4:], item=item)
    refresh_outbox(root, state)
    return {"status": "registered", "reminder_id": rid, "added": True, "item_state": "active"}


def cancel(root: Path, rid: str) -> dict[str, Any]:
    valid_id(rid, "reminder_id")
    state = load_journal(root)
    row = state["items"].get(rid)
    if row is None:
        raise ReminderError("NOT_FOUND")
    if row["status"] == "cancelled":
        refresh_outbox(root, state)
        return {"status": "cancelled", "reminder_id": rid, "changed": False}
    if row["status"] != "active":
        raise ReminderError("INVALID_TRANSITION")
    append(root, state, "cancelled", now_utc(), event_id="can-" + rid[4:], reminder_id=rid)
    refresh_outbox(root, state)
    return {"status": "cancelled", "reminder_id": rid, "changed": True}


def reschedule(root: Path, rid: str, raw: Any) -> dict[str, Any]:
    valid_id(rid, "reminder_id")
    due = validate_due(raw)
    state = load_journal(root)
    old = state["items"].get(rid)
    if old is None:
        raise ReminderError("NOT_FOUND")
    new = {**old["item"], "due": due}
    new_id = item_id(new)
    if new_id == rid and old["status"] == "active":
        if new != old["item"]:
            raise ReminderError("CONFLICTING_IDENTITY", "Same due instant with a different representation")
        refresh_outbox(root, state)
        return {"status": "rescheduled", "old_id": rid, "new_id": new_id, "changed": False}
    if old["status"] == "cancelled" and old["rescheduled_to"] == new_id and state["items"].get(new_id, {}).get("item") == new:
        refresh_outbox(root, state)
        return {"status": "rescheduled", "old_id": rid, "new_id": new_id, "changed": False}
    if old["status"] != "active" or new_id in state["items"]:
        raise ReminderError("INVALID_TRANSITION")
    append(root, state, "rescheduled", now_utc(), event_id="res-" + digest([rid, new_id])[:40], from_id=rid, item=new)
    refresh_outbox(root, state)
    return {"status": "rescheduled", "old_id": rid, "new_id": new_id, "changed": True}


def validate_receipt(raw: Any, oid: str) -> dict[str, str]:
    receipt = exact_keys(raw, {"schema_version", "status", "outbox_id", "consumer_id", "receipt_id"}, "receipt")
    if type(receipt["schema_version"]) is not int or receipt["schema_version"] != VERSION or receipt["status"] != "accepted":
        raise ReminderError("BAD_RECEIPT")
    if receipt["outbox_id"] != oid:
        raise ReminderError("RECEIPT_MISMATCH")
    valid_id(receipt["consumer_id"], "consumer_id")
    valid_id(receipt["receipt_id"], "receipt_id")
    return receipt


def acknowledge(root: Path, oid: str, receipt_json: Any) -> dict[str, Any]:
    valid_id(oid, "outbox_id")
    receipt = validate_receipt(receipt_json, oid)
    state = load_journal(root)
    entry = state["outbox"].get(oid)
    if entry is None:
        raise ReminderError("NOT_FOUND")
    if entry["delivery_state"] == "delivered":
        if entry["consumer_receipt_id"] != receipt["receipt_id"] or entry["consumer_id"] != receipt["consumer_id"]:
            raise ReminderError("RECEIPT_CONFLICT")
        refresh_outbox(root, state)
        return {"status": "delivery_attested", "outbox_id": oid, "changed": False, "consumer_verified": False}
    append(root, state, "delivery_attested", now_utc(), event_id="ack-" + digest([oid, receipt["receipt_id"], receipt["consumer_id"]])[:40],
           outbox_id=oid, receipt_id=receipt["receipt_id"], consumer_id=receipt["consumer_id"])
    refresh_outbox(root, state)
    return {"status": "delivery_attested", "outbox_id": oid, "changed": True, "consumer_verified": False}


def report(root: Path, *, pending_only: bool = False) -> dict[str, Any]:
    state = load_journal(root)
    check_orphans(root)
    expected = current_outbox(state)
    flags = []
    path = root / OUTBOX
    if path.exists():
        try:
            actual = read_json(path)
        except ReminderError:
            flags.append("outbox:unreadable")
        else:
            if actual != expected:
                flags.append("outbox:stale")
    else:
        flags.append("outbox:missing")
    rows = [dict({"reminder_id": rid, "status": item["status"]}, **item["item"])
            for rid, item in sorted(state["items"].items())]
    outgoing = [e for e in expected["entries"] if e["delivery_state"] == "pending"] if pending_only else expected["entries"]
    return {"status": "ok", "items": rows if not pending_only else [], "outbox": outgoing,
            "pending_count": sum(x["delivery_state"] == "pending" for x in expected["entries"]),
            "delivered_attested_count": sum(x["delivery_state"] == "delivered" for x in expected["entries"]),
            "derived_warnings": flags, "last_seq": state["next_seq"] - 1, "external_delivery": "NONE"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local one-shot deadline state and outbox; no external delivery")
    parser.add_argument("--state-dir", type=Path, required=True, help="Existing private directory OUTSIDE checkout")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("register")
    p.add_argument("--file", type=Path, required=True)
    p = sub.add_parser("cancel")
    p.add_argument("--reminder-id", required=True)
    p = sub.add_parser("reschedule")
    p.add_argument("--reminder-id", required=True)
    p.add_argument("--due-file", type=Path, required=True)
    p = sub.add_parser("check")
    p.add_argument("--at-utc", help="Only for synthetic tests: UTC ISO8601 exact seconds")
    sub.add_parser("list")
    sub.add_parser("outbox")
    sub.add_parser("repair-outbox")
    sub.add_parser("failures")
    p = sub.add_parser("ack")
    p.add_argument("--outbox-id", required=True)
    p.add_argument("--receipt-file", type=Path, required=True, help="Externally asserted durable acceptance, NOT authenticated")
    args = parser.parse_args(argv)
    try:
        root = validate_root(args.state_dir)
        with Lock(root):
            if args.command == "register":
                value = register(root, read_json(args.file))
            elif args.command == "cancel":
                value = cancel(root, args.reminder_id)
            elif args.command == "reschedule":
                value = reschedule(root, args.reminder_id, read_json(args.due_file))
            elif args.command == "check":
                when = parse_stamp(args.at_utc, utc=True) if args.at_utc else now_utc()
                value = run_check(root, when)
            elif args.command == "list":
                value = report(root)
            elif args.command == "outbox":
                value = report(root, pending_only=True)
            elif args.command == "repair-outbox":
                state = load_journal(root)
                refresh_outbox(root, state)
                value = {"status": "repaired", "last_seq": state["next_seq"] - 1, "journal_modified": False}
            elif args.command == "failures":
                value = {"status": "ok", "failure_state": read_json(root / FAILURES) if (root / FAILURES).exists() else None}
            elif args.command == "ack":
                value = acknowledge(root, args.outbox_id, read_json(args.receipt_file))
            else:
                raise ReminderError("INVALID_COMMAND")
        print(json.dumps(value, sort_keys=True, ensure_ascii=False))
        return 0
    except ReminderError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "message": str(exc) if exc.code in {"INVALID_ID", "BAD_SCHEMA", "BAD_TIME"} else "Operation failed; see code"}, sort_keys=True))
        return 3 if exc.code == "LOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
