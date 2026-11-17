#!/usr/bin/env python3
"""Read-only Markdown task-ledger format checker. GPL-3.0-only."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

STATES = frozenset(("未投入", "実行中", "完了", "本人保留"))
COLUMNS = frozenset(("作業", "状態", "承認・指示", "実体・根拠", "更新"))
REQUIRED = frozenset(("作業", "状態"))
FENCE = re.compile(r"^ {0,3}(\x60{3,}|~{3,})(.*)$")
BULLET = re.compile(r"^ {0,3}[-+*] +(.+?)\s*$")
MARKER = re.compile(r"^\[([^\]]+)\](?:\s+|$)")
PATH = re.compile(r"(?<![\w:/])(?:~/|/(?!/))[A-Za-z0-9_./@+~%=-]+")
BACKTICK_PATH = re.compile(r"\x60((?:~/|/)[^\x60\r\n]+)\x60")
WINDOWS_PATH = re.compile(r"(?<![\w])(?:[A-Za-z]:\\|\\\\)[^\s\x60|<>]+")


def cells(line: str) -> list[str] | None:
    """Split only unescaped Markdown pipes (odd-backslash escaping)."""
    parts: list[str] = []
    buf: list[str] = []
    backslashes = 0
    found = False
    for ch in line.strip():
        if ch == "|" and backslashes % 2 == 0:
            parts.append("".join(buf).strip())
            buf = []
            found = True
        else:
            buf.append(ch)
        backslashes = backslashes + 1 if ch == "\\" else 0
    if not found:
        return None
    parts.append("".join(buf).strip())
    if line.strip().startswith("|"):
        parts.pop(0)
    stripped = line.strip()
    if stripped.endswith("|"):
        preceding_backslashes = len(stripped[:-1]) - len(stripped[:-1].rstrip("\\"))
        if preceding_backslashes % 2 == 0:
            parts.pop()
    return parts


def is_separator(row: list[str] | None) -> bool:
    return bool(row) and all(re.fullmatch(r":?-{3,}:?", x) for x in row)


def issue(kind: str, line: int, title: str = "", **extra: object) -> dict[str, object]:
    return {"type": kind, "line": line, "title": title, **extra}


def path_candidates(text: str) -> list[str]:
    """Conservative, OS-native absolute/home path recognition only."""
    found: list[str] = []
    for m in BACKTICK_PATH.finditer(text):
        found.append(m.group(1).strip())
    without_ticks = BACKTICK_PATH.sub(" ", text)
    for m in PATH.finditer(without_ticks):
        candidate = m.group().rstrip(".,;:)]}>")
        if candidate:
            found.append(candidate)
    if os.name == "nt":
        found.extend(m.group().rstrip(".,;:)]}>") for m in WINDOWS_PATH.finditer(without_ticks))
    return list(dict.fromkeys(found))


def check_path(token: str) -> str | None:
    """Return missing/unverifiable or None; never follow paths across OS styles."""
    if token.startswith("~/"):
        actual = Path.home() / token[2:]
    elif os.path.isabs(token):
        actual = Path(token)
    else:
        return None
    try:
        actual.stat()
    except (FileNotFoundError, NotADirectoryError):
        return "reference_missing"
    except (PermissionError, OSError):
        return "reference_unverifiable"
    return None


def scan(text: str, allow_completed: bool = False) -> dict[str, object]:
    lines = text.splitlines()
    findings: list[dict[str, object]] = []
    seen: dict[str, int] = {}
    canonical: list[str] | None = None
    excluded_table = False
    fence_char = ""
    fence_len = 0
    count = 0
    items: list[tuple[int, str, str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        number = i + 1
        fence = FENCE.match(line)
        if fence:
            mark = fence.group(1)
            if not fence_char:
                fence_char, fence_len = mark[0], len(mark)
            elif mark[0] == fence_char and len(mark) >= fence_len and not fence.group(2).strip():
                fence_char = ""
            i += 1
            continue
        if fence_char:
            i += 1
            continue
        row = cells(line)
        next_row = cells(lines[i + 1]) if i + 1 < len(lines) else None
        if row and next_row and is_separator(next_row) and len(row) == len(next_row):
            if canonical is None:
                if REQUIRED & set(row):
                    unknown = [x for x in row if x not in COLUMNS]
                    duplicates = sorted({x for x in row if row.count(x) > 1})
                    missing = sorted(REQUIRED - set(row))
                    if unknown or duplicates or missing:
                        findings.append(issue("invalid_header", number, unknown=unknown,
                                              duplicate_columns=duplicates, missing_columns=missing))
                        excluded_table = True
                    else:
                        canonical = row
                        excluded_table = False
                else:
                    excluded_table = True
            else:
                excluded_table = row != canonical
            i += 2
            continue
        if excluded_table:
            if row is not None:
                i += 1
                continue
            excluded_table = False
        if canonical is not None and row is not None:
            if len(row) != len(canonical):
                findings.append(issue("column_count", number, expected=len(canonical), actual=len(row)))
                i += 1
                continue
            values = dict(zip(canonical, row))
            title = values["作業"].strip()
            state = values["状態"].strip()
            if not title:
                findings.append(issue("missing_title", number))
            if not state:
                findings.append(issue("missing_state", number, title))
            elif state not in STATES:
                findings.append(issue("invalid_state", number, title, value=state))
            if title:
                items.append((number, title, state, " ".join(values.values())))
                count += 1
            i += 1
            continue
        bullet = BULLET.match(line)
        if bullet:
            body = bullet.group(1)
            markers: list[str] = []
            while True:
                m = MARKER.match(body)
                if not m:
                    break
                markers.append(m.group(1))
                body = body[m.end():]
            title = body.strip()
            state_markers = [m for m in markers if m != "合図待ち"]
            state = state_markers[0] if state_markers else ""
            if not title:
                findings.append(issue("missing_title", number))
            if not state:
                findings.append(issue("missing_state", number, title))
            elif len(state_markers) != 1 or state not in STATES:
                findings.append(issue("invalid_state", number, title, value=state))
            if markers.count("合図待ち") > 1:
                findings.append(issue("duplicate_wait_marker", number, title))
            if title:
                detail = []
                j = i + 1
                while j < len(lines) and (lines[j].startswith("  ") or lines[j].startswith("\t")):
                    detail.append(lines[j].strip())
                    j += 1
                items.append((number, title, state, " ".join((title, *detail))))
                count += 1
                i = j
                continue
        i += 1
    for number, title, state, content in items:
        if title in seen:
            findings.append(issue("duplicate_title", number, title, first_line=seen[title]))
        else:
            seen[title] = number
        if state == "完了" and not allow_completed:
            findings.append(issue("completed_retained", number, title))
        for path in path_candidates(content):
            status = check_path(path)
            if status:
                findings.append(issue(status, number, title, path=path))
    findings.sort(key=lambda x: (int(x["line"]), str(x["type"])))
    return {"status": "issues" if findings else "ok", "entries": count, "issues": findings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Markdown ledger syntax checker")
    parser.add_argument("ledger", type=Path, help="One local Markdown ledger")
    parser.add_argument("--allow-completed", action="store_true",
                        help="Do not flag retained completed items")
    args = parser.parse_args(argv)
    try:
        text = args.ledger.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print(json.dumps({"status": "error", "message": "Unable to read ledger"}))
        return 1
    result = scan(text, allow_completed=args.allow_completed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
