#!/usr/bin/env python3
"""A read-only filesystem tag omission watcher with durable local delivery state.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only

State is writable (outside watched roots); watched roots are never modified.
This pilot deliberately has no external delivery integration or background scheduler.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

EXCLUDED_DIRS = frozenset({".git", "node_modules", "__pycache__", "venv", ".venv", ".trash"})
RECORD_NAME = ".retention_records.json"
STATE_NAME = "untagged-watch-state.json"
LOCK_NAME = ".untagged-watch.lock"
RELATIVE = re.compile(r"^[^\\\x00-\x1f\x7f]+$")


class WatchFailure(Exception):
    """Processing could not be completed safely."""


class LockBusy(WatchFailure):
    """A previous invocation owns the lock file."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def relative_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or not RELATIVE.fullmatch(raw):
        raise WatchFailure("Invalid relative path in configuration or record")
    if raw.startswith("/") or raw.startswith("~/") or re.match(r"^[a-zA-Z]:", raw):
        raise WatchFailure("Absolute path in a relative-path field")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise WatchFailure("Unsafe relative path component")
    return raw


def check_real_dir(path: Path, label: str) -> Path:
    absolute = Path(os.path.abspath(path))
    for parent in reversed((absolute, *absolute.parents)):
        try:
            if stat.S_ISLNK(parent.lstat().st_mode):
                raise WatchFailure(f"{label} traverses a symbolic link")
        except OSError as exc:
            raise WatchFailure(f"{label} is inaccessible") from exc
    if not stat.S_ISDIR(absolute.lstat().st_mode):
        raise WatchFailure(f"{label} is not a directory")
    return absolute


def load_config(path: Path, state_dir: Path) -> dict[str, Any]:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise WatchFailure("Cannot read configuration") from exc
    if not isinstance(cfg, dict) or set(cfg) != {"version", "roots"} or type(cfg["version"]) is not int or cfg["version"] != 1:
        raise WatchFailure("Unsupported configuration schema")
    if not isinstance(cfg["roots"], list) or not cfg["roots"]:
        raise WatchFailure("One or more roots are required")

    roots = []
    names: set[str] = set()
    paths: list[Path] = []
    for raw in cfg["roots"]:
        if not isinstance(raw, dict) or not {"name", "path"} <= raw.keys() or set(raw) - {"name", "path", "exclude_subtrees"}:
            raise WatchFailure("Invalid root configuration")
        name, value = raw["name"], raw["path"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", name) or name in names:
            raise WatchFailure("Root names must be unique short safe identifiers")
        if not isinstance(value, str) or not value.strip():
            raise WatchFailure("Root path is invalid")
        roots_path = Path(value).expanduser()
        if not roots_path.is_absolute():
            roots_path = path.parent / roots_path
        absolute = check_real_dir(roots_path, "Watched root")
        excluded = raw.get("exclude_subtrees", [])
        if not isinstance(excluded, list) or not all(isinstance(x, str) for x in excluded):
            raise WatchFailure("exclude_subtrees must be a list of relative paths")
        excluded_set = sorted(set(relative_path(x) for x in excluded))
        for old in paths:
            if absolute == old or absolute in old.parents or old in absolute.parents:
                raise WatchFailure("Watched roots must not overlap")
        if state_dir == absolute or state_dir in absolute.parents or absolute in state_dir.parents:
            raise WatchFailure("State directory must be separate from watched roots")
        names.add(name)
        paths.append(absolute)
        roots.append({"name": name, "path": absolute, "exclude_subtrees": excluded_set})
    contract = [{"name": root["name"], "path": str(root["path"]), "exclude_subtrees": root["exclude_subtrees"]} for root in roots]
    return {"roots": roots, "fingerprint": digest({"version": 1, "roots": contract})}


def load_records(root: Path) -> set[str]:
    record = root / RECORD_NAME
    try:
        if not stat.S_ISREG(record.lstat().st_mode):
            raise WatchFailure("Retention record is not a regular file")
        raw = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise WatchFailure("Retention record is missing, unreadable or malformed") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("entries"), list):
        raise WatchFailure("Retention record entries must be a list")
    if "version" in raw and (type(raw["version"]) is not int or raw["version"] != 1):
        raise WatchFailure("Unknown retention record schema version")
    known: set[str] = set()
    for entry in raw["entries"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("class"), str) or not entry["class"].strip():
            raise WatchFailure("Invalid retention record entry")
        path = relative_path(entry["path"])
        if path in known:
            raise WatchFailure("Duplicate retention record entry")
        known.add(path)
        # Unrecognized nonblank class is HOLD at this checker boundary,
        # never interpreted as permission to delete or as an absent tag.
    return known


def excluded(path: str, exclusions: list[str]) -> bool:
    return any(path == entry or path.startswith(entry + "/") for entry in exclusions)


def scan_root(root: dict[str, Any]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    base: Path = root["path"]
    known = load_records(base)
    seen: set[tuple[str, str]] = set()
    untagged: set[tuple[str, str]] = set()

    def onerror(exc: OSError) -> None:
        raise WatchFailure("Directory scan failed") from exc

    try:
        for directory, dirs, files in os.walk(base, topdown=True, followlinks=False, onerror=onerror):
            parent = Path(directory)
            folder_rel = parent.relative_to(base).as_posix()
            remaining = []
            for name in dirs:
                rel = name if folder_rel == "." else folder_rel + "/" + name
                if name in EXCLUDED_DIRS or excluded(rel, root["exclude_subtrees"]):
                    continue
                probe = parent / name
                try:
                    mode = probe.lstat().st_mode
                except OSError as exc:
                    raise WatchFailure("Directory entry cannot be examined") from exc
                if stat.S_ISLNK(mode):
                    continue
                if stat.S_ISDIR(mode):
                    remaining.append(name)
            dirs[:] = remaining
            for name in files:
                rel = name if folder_rel == "." else folder_rel + "/" + name
                if rel == RECORD_NAME or excluded(rel, root["exclude_subtrees"]):
                    continue
                probe = parent / name
                try:
                    mode = probe.lstat().st_mode
                except OSError as exc:
                    raise WatchFailure("File entry cannot be examined") from exc
                if not stat.S_ISREG(mode):
                    continue
                item = root["name"], rel
                seen.add(item)
                if rel not in known:
                    untagged.add(item)
    except OSError as exc:
        raise WatchFailure("Directory scan could not be completed") from exc
    return seen, untagged


def encode_seen(items: set[tuple[str, str]]) -> list[list[str]]:
    return [list(x) for x in sorted(items)]


def decode_seen(raw: object, roots: set[str]) -> set[tuple[str, str]]:
    if not isinstance(raw, list):
        raise WatchFailure("Invalid seen snapshot")
    items: set[tuple[str, str]] = set()
    for entry in raw:
        if not isinstance(entry, list) or len(entry) != 2 or not isinstance(entry[0], str) or entry[0] not in roots:
            raise WatchFailure("Malformed seen entry")
        path = relative_path(entry[1])
        pair = (entry[0], path)
        if pair in items:
            raise WatchFailure("Duplicate seen entry")
        items.add(pair)
    return items


def read_state(state_path: Path, fingerprint: str, names: set[str]) -> dict[str, Any] | None:
    try:
        if stat.S_ISLNK(state_path.lstat().st_mode):
            raise WatchFailure("State file must not be a symbolic link")
        raw_bytes = state_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WatchFailure("State file inaccessible") from exc
    try:
        envelope = json.loads(raw_bytes)
    except (ValueError, UnicodeError) as exc:
        raise WatchFailure("State JSON is corrupt") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "sha256"} or not isinstance(envelope["sha256"], str):
        raise WatchFailure("State envelope is invalid")
    state = envelope["payload"]
    if digest(state) != envelope["sha256"]:
        raise WatchFailure("State integrity hash mismatch")
    if not isinstance(state, dict) or set(state) != {"version", "config_fingerprint", "baseline_complete", "seen", "pending"}:
        raise WatchFailure("Unsupported state schema")
    if type(state["version"]) is not int or state["version"] != 1 or state["baseline_complete"] is not True:
        raise WatchFailure("Incomplete or unsupported state")
    if state["config_fingerprint"] != fingerprint:
        raise WatchFailure("Configuration changed; explicit migration required")
    decode_seen(state["seen"], names)
    pending = state["pending"]
    if pending is not None:
        if not isinstance(pending, dict) or set(pending) != {"event_id", "report", "next_seen"}:
            raise WatchFailure("Invalid pending state")
        if not isinstance(pending["event_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", pending["event_id"]):
            raise WatchFailure("Invalid pending event identifier")
        if not isinstance(pending["report"], dict) or pending["report"].get("event_id") != pending["event_id"]:
            raise WatchFailure("Pending report does not match event")
        decode_seen(pending["next_seen"], names)
    return state


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    envelope = {"payload": state, "sha256": digest(state)}
    encoded = canonical_json(envelope) + b"\n"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=state_path.parent, prefix=".state-temp-", delete=False) as stream:
            temp_path = Path(stream.name)
            if os.name != "nt":
                os.fchmod(stream.fileno(), 0o600)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, state_path)
        temp_path = None
        if os.name != "nt":
            fd = os.open(state_path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    except OSError as exc:
        raise WatchFailure("Could not commit local state") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


class FileLock:
    def __init__(self, state_dir: Path):
        self.path = state_dir / LOCK_NAME
        self.fd: int | None = None

    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(self.fd, b"busy\n")
        except FileExistsError as exc:
            raise LockBusy("Another run may be active; examine lock before manual recovery") from exc
        except OSError as exc:
            raise WatchFailure("Cannot create state lock") from exc
        return self

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
            try:
                self.path.unlink()
            except OSError:
                # Conservative: future runs will stop until operator checks the lock.
                pass


def scan(config: dict[str, Any], state_path: Path) -> dict[str, Any]:
    # A crash before atomic rename can leave an orphaned state temporary file.
    # In particular, do NOT silently create a new baseline in that situation.
    try:
        orphaned = any(p.name.startswith(".state-temp-") for p in state_path.parent.iterdir())
    except OSError as exc:
        raise WatchFailure("Unable to examine state directory") from exc
    if orphaned:
        raise WatchFailure("Interrupted state save detected; manual inspection required")
    roots = config["roots"]
    names = {root["name"] for root in roots}
    state = read_state(state_path, config["fingerprint"], names)
    if state is not None and state["pending"] is not None:
        return {"status": "pending", "delivery": "unconfirmed", "report": state["pending"]["report"]}

    current: set[tuple[str, str]] = set()
    untagged: set[tuple[str, str]] = set()
    for root in roots:
        observed, missing_tag = scan_root(root)
        current.update(observed)
        untagged.update(missing_tag)

    if state is None:
        state = {"version": 1, "config_fingerprint": config["fingerprint"],
                 "baseline_complete": True, "seen": encode_seen(current), "pending": None}
        save_state(state_path, state)
        return {"status": "baseline", "observed_files": len(current), "new_untagged": 0}

    previous = decode_seen(state["seen"], names)
    newcomers = sorted(untagged - previous)
    if not newcomers:
        state["seen"] = encode_seen(current)
        save_state(state_path, state)
        return {"status": "ok", "observed_files": len(current), "new_untagged": 0}

    event_id = uuid.uuid4().hex
    report = {
        "event_id": event_id,
        "when_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "where": "configured local root(s)",
        "who": "untagged_watch",
        "what": "new_untagged_files",
        "why": "newly observed regular files are absent from the root retention records",
        "how": "read-only recursive scan compared against verified seen state",
        "count": len(newcomers),
        "items": [{"root": name, "relative_path": rel} for name, rel in newcomers],
    }
    state["pending"] = {"event_id": event_id, "report": report, "next_seen": encode_seen(current)}
    # Durable pending MUST be on disk before this event is emitted.
    save_state(state_path, state)
    return {"status": "pending", "delivery": "unconfirmed", "report": report}


def ack(config: dict[str, Any], state_path: Path, event_id: str) -> dict[str, Any]:
    try:
        orphaned = any(p.name.startswith(".state-temp-") for p in state_path.parent.iterdir())
    except OSError as exc:
        raise WatchFailure("Unable to examine state directory") from exc
    if orphaned:
        raise WatchFailure("Interrupted state save detected; manual inspection required")
    state = read_state(state_path, config["fingerprint"], {r["name"] for r in config["roots"]})
    if state is None or state["pending"] is None:
        raise WatchFailure("No pending event to acknowledge")
    if event_id != state["pending"]["event_id"]:
        raise WatchFailure("Event identifier mismatch")
    state["seen"] = state["pending"]["next_seen"]
    state["pending"] = None
    save_state(state_path, state)
    return {"status": "acknowledged", "event_id": event_id}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only new-untagged-file watcher")
    parser.add_argument("command", choices=("scan", "ack"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--event-id", help="Required for ack, only after durable downstream acceptance")
    args = parser.parse_args(argv)
    try:
        state_dir = check_real_dir(args.state_dir, "State directory")
        checkout = Path(__file__).resolve().parents[1]
        if state_dir == checkout or checkout in state_dir.parents:
            raise WatchFailure("State directory must be outside the public project checkout")
        cfg = load_config(args.config, state_dir)
        with FileLock(state_dir):
            if args.command == "ack":
                if not args.event_id:
                    raise WatchFailure("ack requires --event-id")
                result = ack(cfg, state_dir / STATE_NAME, args.event_id)
            else:
                if args.event_id:
                    raise WatchFailure("--event-id is only valid with ack")
                result = scan(cfg, state_dir / STATE_NAME)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except LockBusy as exc:
        print(json.dumps({"status": "locked", "message": str(exc)}))
        return 3
    except (WatchFailure, OSError) as exc:
        # Do not echo any locally sensitive paths, filenames or file contents.
        message = str(exc) if isinstance(exc, WatchFailure) else "Unexpected filesystem error"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
