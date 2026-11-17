#!/usr/bin/env python3
"""Propose file-lifetime decisions from predeclared tags and file mtimes.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only

No filesystem mutation, including trash moves, purge, retention-tag editing, state
files, snapshots or log writes. This is a proposal-only public pilot.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

RECORD_NAME = ".retention_records.json"
EXCLUDED_DIRS = frozenset({".git", "node_modules", "__pycache__", "venv", ".venv", ".trash"})
ROOT_NAME = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
DRIVE = re.compile(r"^[A-Za-z]:")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
DAY_NS = 86_400_000_000_000
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


class OrganizerError(Exception):
    """Cannot safely interpret the supplied configuration or record."""


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise OrganizerError("Duplicate JSON object key")
        obj[key] = value
    return obj


def reject_constant(_value: str) -> None:
    raise OrganizerError("Nonstandard JSON numeric constant")


def load_json(path: Path, purpose: str) -> object:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=no_duplicate_keys,
                             parse_constant=reject_constant)
    except OrganizerError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise OrganizerError(f"Cannot read valid {purpose} JSON") from exc


def existing_real_directory(path: Path, label: str) -> Path:
    abs_path = Path(os.path.abspath(path))
    for component in reversed((abs_path, *abs_path.parents)):
        try:
            if stat.S_ISLNK(component.lstat().st_mode):
                raise OrganizerError(f"{label} traverses a symbolic link")
        except OSError as exc:
            raise OrganizerError(f"{label} is not accessible") from exc
    try:
        if not stat.S_ISDIR(abs_path.lstat().st_mode):
            raise OrganizerError(f"{label} must be an existing directory")
    except OSError as exc:
        raise OrganizerError(f"{label} is not accessible") from exc
    return abs_path


def root_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "~")) or DRIVE.match(raw):
        return None
    if CONTROL.search(raw) or "\\" in raw:
        return None
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return raw


def load_config(config_path: Path) -> dict[str, Any]:
    config = load_json(config_path, "configuration")
    if not isinstance(config, dict) or set(config) != {"version", "roots", "age_days"}:
        raise OrganizerError("Unsupported configuration schema")
    if type(config["version"]) is not int or config["version"] != 1:
        raise OrganizerError("Unsupported configuration version")
    age_days = config["age_days"]
    if type(age_days) is not int or age_days < 0 or age_days > 365_000:
        raise OrganizerError("age_days must be an integer from 0 to 365000")
    if not isinstance(config["roots"], list) or not config["roots"]:
        raise OrganizerError("Configuration requires one or more roots")
    names: set[str] = set()
    locations: list[Path] = []
    roots: list[dict[str, Any]] = []
    for entry in config["roots"]:
        if not isinstance(entry, dict) or set(entry) != {"name", "path", "exclude_subtrees"}:
            raise OrganizerError("Invalid root configuration")
        name = entry["name"]
        if not isinstance(name, str) or not ROOT_NAME.fullmatch(name) or name in names:
            raise OrganizerError("Root names must be unique safe identifiers")
        names.add(name)
        value = entry["path"]
        if not isinstance(value, str) or not value or CONTROL.search(value):
            raise OrganizerError("Invalid root path")
        base = existing_real_directory(config_path.parent / value, "Root directory")
        if any(base == previous or base in previous.parents or previous in base.parents
               for previous in locations):
            raise OrganizerError("Configured roots must not overlap")
        locations.append(base)
        excludes = entry["exclude_subtrees"]
        if not isinstance(excludes, list):
            raise OrganizerError("exclude_subtrees must be a list")
        checked: set[str] = set()
        for exclusion in excludes:
            clean = root_relative(exclusion)
            if clean is None or clean in checked:
                raise OrganizerError("Unsafe or duplicate exclusion")
            checked.add(clean)
        roots.append({"name": name, "path": base, "exclude_subtrees": checked})
    return {"roots": roots, "age_days": age_days}


def is_excluded(path: str, exclusions: set[str]) -> bool:
    parts = path.split("/")
    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    return any(path == excluded or path.startswith(excluded + "/") for excluded in exclusions)


def read_records(root: Path) -> list[dict[str, Any]]:
    path = root / RECORD_NAME
    try:
        if stat.S_ISLNK(path.lstat().st_mode):
            raise OrganizerError("Retention record cannot be a symbolic link")
    except OSError as exc:
        raise OrganizerError("Retention record is missing or inaccessible") from exc
    data = load_json(path, "retention record")
    if not isinstance(data, dict) or set(data) not in ({"entries"}, {"version", "entries"}):
        raise OrganizerError("Unsupported retention record schema")
    if "version" in data and (type(data["version"]) is not int or data["version"] != 1):
        raise OrganizerError("Unsupported retention record version")
    if not isinstance(data["entries"], list):
        raise OrganizerError("Retention record entries must be a list")
    result: list[dict[str, Any]] = []
    encountered: set[str] = set()
    for index, row in enumerate(data["entries"]):
        if not isinstance(row, dict) or set(row) != {"path", "class"}:
            # Only a safe index is emitted. No guesses about malformed entries.
            result.append({"index": index, "relative_path": None, "class": None,
                           "record_error": "MALFORMED_ENTRY"})
            continue
        raw_path = row["path"]
        rel = root_relative(raw_path)
        if rel is not None:
            if rel in encountered:
                raise OrganizerError("Duplicate retention record path")
            encountered.add(rel)
        cls = row["class"]
        result.append({"index": index, "relative_path": rel,
                       "class": cls if isinstance(cls, str) else None,
                       "record_error": "UNSAFE_RECORD_PATH" if rel is None else None})
    return result


def file_lstat(root: Path, relative: str) -> os.stat_result:
    """Examine each component with lstat and refuse symlink traversals."""
    candidate = root
    parts = relative.split("/")
    for index, component in enumerate(parts):
        candidate = candidate / component
        try:
            info = candidate.lstat()
        except FileNotFoundError as exc:
            raise OrganizerError("MISSING_REGISTERED_FILE") from exc
        except (OSError, ValueError) as exc:
            raise OrganizerError("INACCESSIBLE_REGISTERED_FILE") from exc
        if stat.S_ISLNK(info.st_mode):
            raise OrganizerError("SYMLINK_PATH")
        if index != len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise OrganizerError("NOT_A_DIRECTORY")
    if not stat.S_ISREG(info.st_mode):
        raise OrganizerError("NOT_REGULAR_FILE")
    return info


def datetime_ns(instant: dt.datetime) -> int:
    if not isinstance(instant, dt.datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise OrganizerError("as_of must have an explicit UTC offset")
    delta = instant.astimezone(dt.timezone.utc) - EPOCH
    return ((delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds) * 1_000


def evaluate(root: dict[str, Any], record: dict[str, Any], as_of_ns: int,
             age_days: int) -> dict[str, Any]:
    path = record["relative_path"]
    label = {"root": root["name"], "record_index": record["index"],
             "relative_path": path, "tag_class": record["class"],
             "decision": "hold", "reason": None, "age_seconds": None,
             "threshold_days": age_days}
    if record["record_error"] is not None:
        label["reason"] = record["record_error"]
        return label
    if path == RECORD_NAME or is_excluded(path, root["exclude_subtrees"]):
        label.update(decision="excluded", reason="EXCLUDED_BY_SCOPE")
        return label
    tag = record["class"]
    if tag not in ("disposable", "permanent"):
        label["reason"] = "UNKNOWN_TAG_CLASS"
        return label
    try:
        info = file_lstat(root["path"], path)
    except OrganizerError as exc:
        label["reason"] = str(exc)
        return label
    if tag == "permanent":
        label.update(decision="excluded", reason="PERMANENT_TAG")
        return label
    elapsed = as_of_ns - info.st_mtime_ns
    if elapsed < 0:
        label["reason"] = "FUTURE_MODIFICATION_TIME"
        return label
    label["age_seconds"] = elapsed // 1_000_000_000
    if elapsed >= age_days * DAY_NS:
        label.update(decision="candidate", reason="DISPOSABLE_MTIME_AGE_AT_LEAST_THRESHOLD")
    else:
        label.update(decision="not_due", reason="DISPOSABLE_MTIME_AGE_BELOW_THRESHOLD")
    return label


def propose(config: dict[str, Any], *, as_of: dt.datetime | None = None) -> dict[str, Any]:
    instant = as_of if as_of is not None else dt.datetime.now(dt.timezone.utc)
    instant_ns = datetime_ns(instant)
    report = []
    for root in config["roots"]:
        rows = read_records(root["path"])
        report.extend(evaluate(root, row, instant_ns, config["age_days"]) for row in rows)
    decisions = ("candidate", "not_due", "excluded", "hold")
    counts = {kind: sum(item["decision"] == kind for item in report) for kind in decisions}
    return {
        "status": "partial" if counts["hold"] else "candidates" if counts["candidate"] else "ok",
        "as_of_utc": instant.astimezone(dt.timezone.utc).isoformat(),
        "age_threshold_days": config["age_days"],
        "counts": counts,
        "items": report,
        "unregistered_files_scanned": False,
        "dry_run": True,
        "changed_files": 0,
        "deletion_available": False,
        "trash_move_available": False,
        "purge_available": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retention tag and mtime proposal ONLY; no move or purge")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--as-of", help="Optional ISO time with offset for synthetic tests")
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        instant = None
        if args.as_of is not None:
            try:
                instant = dt.datetime.fromisoformat(args.as_of)
            except ValueError as exc:
                raise OrganizerError("Invalid as-of timestamp") from exc
        result = propose(cfg, as_of=instant)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1 if result["status"] == "partial" else 0
    except (OrganizerError, OSError) as exc:
        # No raw filesystem paths, record contents or exception repr in stdout.
        message = str(exc) if isinstance(exc, OrganizerError) else "Filesystem operation failed"
        print(json.dumps({"status": "error", "message": message,
                          "dry_run": True, "changed_files": 0}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
