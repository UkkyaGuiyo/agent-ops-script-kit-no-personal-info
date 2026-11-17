#!/usr/bin/env python3
"""Read-only local file-size watcher. No network, deletion, or scheduling.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any


class WatchError(Exception):
    """A full, trustworthy scan could not be completed."""


def _load_targets(config_path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WatchError("Unable to read or parse the configuration") from exc

    if not isinstance(raw, dict) or set(raw) != {"targets"}:
        raise WatchError("Configuration must contain only a 'targets' list")
    entries = raw["targets"]
    if not isinstance(entries, list) or not entries:
        raise WatchError("Configuration targets must be a nonempty list")

    names: set[str] = set()
    validated: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"name", "path", "warning_bytes"}:
            raise WatchError("Each target requires name, path, and warning_bytes only")
        name, raw_path, threshold = (entry[k] for k in ("name", "path", "warning_bytes"))
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or name in names:
            raise WatchError("Target name is missing, duplicated, or too long")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise WatchError("Target path must be a nonempty string")
        if type(threshold) is not int or threshold < 0:
            raise WatchError("warning_bytes must be a nonnegative integer")
        names.add(name)
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = config_path.parent / path
        validated.append({"name": name, "path": path, "warning_bytes": threshold})
    return validated


def _scan_one(target: dict[str, Any]) -> dict[str, Any]:
    root = Path(os.path.abspath(target["path"]))
    try:
        # Reject symbolic links in *every* path component; do not resolve first.
        for component in reversed((root, *root.parents)):
            if stat.S_ISLNK(component.lstat().st_mode):
                raise WatchError("Target path cannot contain symbolic links")
        root_stat = root.lstat()
    except OSError as exc:
        raise WatchError("Target directory cannot be accessed") from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise WatchError("Target must be a real directory")

    total_bytes = total_files = skipped_symlinks = 0
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        raise WatchError("A file entry could not be examined") from exc
                    mode = info.st_mode
                    if stat.S_ISLNK(mode):
                        skipped_symlinks += 1
                    elif stat.S_ISDIR(mode):
                        pending.append(Path(entry.path))
                    elif stat.S_ISREG(mode):
                        total_bytes += info.st_size
                        total_files += 1
                    # Sockets, devices, and other special files are skipped.
        except OSError as exc:
            raise WatchError("A directory could not be scanned completely") from exc
    return {
        "name": target["name"],
        "bytes": total_bytes,
        "warning_bytes": target["warning_bytes"],
        "warning": total_bytes >= target["warning_bytes"],
        "files": total_files,
        "skipped_symlinks": skipped_symlinks,
    }


def run(config_path: Path) -> dict[str, Any]:
    targets = _load_targets(config_path)
    # Never expose partial results if one of several targets fails.
    results = [_scan_one(target) for target in targets]
    return {"status": "ok", "targets": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only apparent file-size watcher")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.config)
    except (WatchError, OSError) as exc:
        message = str(exc) if isinstance(exc, WatchError) else "Unexpected filesystem error"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
