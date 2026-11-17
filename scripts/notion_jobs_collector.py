#!/usr/bin/env python3
"""Offline synthetic Notion job snapshot collector. No Notion/network/intake access.

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
from typing import Any, Iterator, Protocol
from urllib.parse import urlsplit, urlunsplit

SCHEMA = 1
POLICY_KEYS = frozenset({"schema_version", "policy_version", "source_id", "parent_page_id", "parent_url", "parent_title", "conditions"})
CONDITION_IDS = frozenset({"new_date_page", "new_url"})
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
DAY_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
URL_RE = re.compile(r"https?://[^\s<>\"'\]\[(){}]+", re.IGNORECASE)
STATE_FILE = "notion-jobs-state.json"
LOCK_FILE = ".notion-jobs.lock"
TEMP_PREFIX = ".notion-jobs-temp-"


class CollectorError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class ChildError(CollectorError):
    pass


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in pairs:
        if k in result:
            raise CollectorError("DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def reject_constant(value: str) -> None:
    raise CollectorError("INVALID_JSON_NUMBER")


def load_json(path: Path) -> Any:
    safe_file(path)
    try:
        raw = path.read_bytes()
        if len(raw) > 4 * 1024 * 1024:
            raise CollectorError("INPUT_TOO_LARGE")
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except CollectorError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError):
        raise CollectorError("BAD_JSON") from None


def canonical(v: object) -> bytes:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(v: object) -> str:
    return hashlib.sha256(canonical(v)).hexdigest()


def safe_file(path: Path, *, missing_ok: bool = False) -> None:
    path = Path(os.path.abspath(path))
    for ancestor in reversed((path, *path.parents)):
        try:
            info = ancestor.lstat()
        except FileNotFoundError:
            if missing_ok and ancestor == path:
                return
            raise CollectorError("MISSING_INPUT") from None
        except OSError:
            raise CollectorError("FILE_ACCESS_ERROR") from None
        if stat.S_ISLNK(info.st_mode):
            raise CollectorError("UNSAFE_SYMLINK")
    if not path.is_file():
        raise CollectorError("NOT_REGULAR_FILE")


def safe_state_dir(root: Path) -> Path:
    root = Path(os.path.abspath(root))
    for ancestor in reversed((root, *root.parents)):
        try:
            info = ancestor.lstat()
        except OSError:
            raise CollectorError("MISSING_STATE_DIR") from None
        if stat.S_ISLNK(info.st_mode):
            raise CollectorError("UNSAFE_SYMLINK")
    if not root.is_dir():
        raise CollectorError("MISSING_STATE_DIR")
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or checkout in root.parents:
        raise CollectorError("STATE_INSIDE_CHECKOUT")
    return root


def parse_scalar(value: str) -> object:
    if value.startswith('"'):
        try:
            ret = json.loads(value)
        except ValueError:
            raise CollectorError("BAD_POLICY_SYNTAX") from None
        if not isinstance(ret, str):
            raise CollectorError("BAD_POLICY_TYPE")
        return ret
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"0|[1-9][0-9]*", value):
        return int(value)
    if re.fullmatch(r"[A-Za-z0-9_.:/-]+", value):
        return value
    raise CollectorError("BAD_POLICY_SYNTAX")


def load_policy(path: Path) -> dict[str, Any]:
    """Strict YAML *subset*: plain top-level scalar keys and two-space conditions map.

    Deliberately rejects general YAML aliases, tags, complex keys, comments, and merges.
    """
    safe_file(path)
    try:
        raw = path.read_bytes()
        if len(raw) > 32_768:
            raise CollectorError("POLICY_TOO_LARGE")
        text = raw.decode("utf-8")
    except CollectorError:
        raise
    except (OSError, UnicodeError):
        raise CollectorError("BAD_POLICY_SYNTAX") from None
    result: dict[str, Any] = {}
    in_conditions = False
    conditions: dict[str, bool] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        if "\t" in line or line.lstrip().startswith("#") or line.rstrip() != line:
            raise CollectorError("BAD_POLICY_SYNTAX")
        if line.startswith("  "):
            if not in_conditions or line.startswith("   "):
                raise CollectorError("BAD_POLICY_SYNTAX")
            m = re.fullmatch(r"  ([a-z_]+): (true|false)", line)
            if not m:
                raise CollectorError("BAD_POLICY_SYNTAX")
            key, state = m.groups()
            if key in conditions:
                raise CollectorError("DUPLICATE_POLICY_KEY")
            if key not in CONDITION_IDS:
                raise CollectorError("UNKNOWN_CONDITION_ID")
            conditions[key] = state == "true"
            continue
        m = re.fullmatch(r"([a-z_]+):(?: (.+))?", line)
        if not m:
            raise CollectorError("BAD_POLICY_SYNTAX")
        k, value = m.groups()
        if k in result:
            raise CollectorError("DUPLICATE_POLICY_KEY")
        if k not in POLICY_KEYS:
            raise CollectorError("UNKNOWN_POLICY_KEY")
        if k == "conditions":
            if value is not None:
                raise CollectorError("BAD_POLICY_SYNTAX")
            result[k] = conditions
            in_conditions = True
        else:
            if value is None:
                raise CollectorError("BAD_POLICY_SYNTAX")
            result[k] = parse_scalar(value)
            in_conditions = False
    if set(result) != POLICY_KEYS or set(conditions) != CONDITION_IDS:
        raise CollectorError("INCOMPLETE_POLICY")
    if type(result["schema_version"]) is not int or result["schema_version"] != SCHEMA:
        raise CollectorError("UNSUPPORTED_POLICY_VERSION")
    for key in ("policy_version", "source_id", "parent_page_id"):
        v = result[key]
        if not isinstance(v, str) or not ID_RE.fullmatch(v):
            raise CollectorError("BAD_POLICY_VALUE")
    if not isinstance(result["parent_title"], str) or not (1 <= len(result["parent_title"]) <= 160):
        raise CollectorError("BAD_POLICY_VALUE")
    if not isinstance(result["parent_url"], str) or not result["parent_url"].startswith("https://"):
        raise CollectorError("BAD_POLICY_VALUE")
    if not any(conditions.values()):
        raise CollectorError("NO_ENABLED_CONDITIONS")
    result["policy_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def valid_date_title(title: str) -> bool:
    if not isinstance(title, str) or not DAY_RE.fullmatch(title):
        return False
    try:
        return dt.date.fromisoformat(title.replace("/", "-")).strftime("%Y/%m/%d") == title
    except ValueError:
        return False


def url_clean(raw: str) -> str:
    s = raw.rstrip(".,;:!?")
    parts = urlsplit(s)
    try:
        port = parts.port
    except ValueError:
        raise CollectorError("INVALID_JOB_URL") from None
    if parts.scheme.lower() not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise CollectorError("INVALID_JOB_URL")
    hostname = parts.hostname.lower()
    if not re.fullmatch(r"[a-z0-9.-]+", hostname) or hostname.startswith("-") or ".." in hostname:
        raise CollectorError("INVALID_JOB_URL")
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", "", ""))


def urls_in_body(text: str) -> list[str]:
    result = set()
    for match in URL_RE.finditer(text):
        try:
            result.add(url_clean(match.group(0)))
        except CollectorError:
            # Invalid URL-looking strings are not actionable; do not execute any text.
            continue
    return sorted(result)


class PageProvider(Protocol):
    """Read-only boundary. No network implementation is bundled."""
    def fetch_parent(self) -> Any: ...
    def fetch_child(self, page_id: str) -> Any: ...


class FixtureProvider:
    """Only bundled provider: fully offline in-memory fixture responses."""
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
    def fetch_parent(self) -> Any:
        return self.raw["parent"]
    def fetch_child(self, page_id: str) -> Any:
        return self.raw["pages"].get(page_id)


def snapshot(path: Path) -> FixtureProvider:
    raw = load_json(path)
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "parent", "pages"}:
        raise CollectorError("BAD_FIXTURE_SCHEMA")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != SCHEMA or not isinstance(raw["pages"], dict):
        raise CollectorError("BAD_FIXTURE_SCHEMA")
    if len(raw["pages"]) > 1000:
        raise CollectorError("TOO_MANY_PAGES")
    return FixtureProvider(raw)


def validate_parent(provider: PageProvider, config: dict[str, Any]) -> list[dict[str, str]]:
    p = provider.fetch_parent()
    if not isinstance(p, dict) or p.get("id") != config["parent_page_id"] or p.get("url") != config["parent_url"] or p.get("title") != config["parent_title"] or type(p.get("body")) is not str or p.get("complete") is not True:
        raise CollectorError("PARENT_VALIDATION_FAILED")
    children = p.get("children")
    if not isinstance(children, list) or len(children) > 1000:
        raise CollectorError("PARENT_VALIDATION_FAILED")
    seen: set[str] = set()
    for child in children:
        if not isinstance(child, dict) or set(child) != {"id", "url", "title"}:
            raise CollectorError("PARENT_VALIDATION_FAILED")
        if not isinstance(child["id"], str) or not ID_RE.fullmatch(child["id"]) or child["id"] in seen:
            raise CollectorError("PARENT_VALIDATION_FAILED")
        if not isinstance(child["url"], str) or not isinstance(child["title"], str):
            raise CollectorError("PARENT_VALIDATION_FAILED")
        seen.add(child["id"])
    return children


def validate_child(provider: PageProvider, child: dict[str, str]) -> list[str]:
    if not valid_date_title(child["title"]):
        raise ChildError("INVALID_DATE_TITLE")
    page = provider.fetch_child(child["id"])
    if page is None:
        raise ChildError("CHILD_FETCH_FAILED")
    if not isinstance(page, dict) or page.get("id") != child["id"] or page.get("url") != child["url"] or page.get("title") != child["title"] or type(page.get("body")) is not str or page.get("complete") is not True:
        raise ChildError("CHILD_VALIDATION_FAILED")
    return urls_in_body(page["body"])


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def validate_state(state: Any, policy: dict[str, Any]) -> dict[str, Any]:
    required = {"schema_version", "policy_version", "policy_sha256", "bootstrap", "seen_pages", "seen_urls", "outbox", "last_success_at", "integrity_sha256"}
    if not isinstance(state, dict) or set(state) != required:
        raise CollectorError("BAD_STATE")
    supplied = state.get("integrity_sha256")
    if not isinstance(supplied, str) or supplied != digest({k: v for k, v in state.items() if k != "integrity_sha256"}):
        raise CollectorError("BAD_STATE_INTEGRITY")
    if type(state["schema_version"]) is not int or state["schema_version"] != SCHEMA:
        raise CollectorError("BAD_STATE")
    if (state["policy_version"], state["policy_sha256"]) != (policy["policy_version"], policy["policy_sha256"]):
        raise CollectorError("POLICY_MISMATCH")
    b = state["bootstrap"]
    if not isinstance(b, dict) or set(b) != {"status", "attempts", "started_at", "completed_at", "history"} or b["status"] not in {"started", "complete"} or type(b["attempts"]) is not int or b["attempts"] < 1:
        raise CollectorError("BAD_STATE")
    if not isinstance(b["history"], list) or len(b["history"]) != b["attempts"]:
        raise CollectorError("BAD_STATE")
    for i, attempt in enumerate(b["history"], 1):
        if not isinstance(attempt, dict) or attempt.get("number") != i or not isinstance(attempt.get("at"), str) or attempt.get("result") not in {"started", "interrupted", "error", "partial", "complete"}:
            raise CollectorError("BAD_STATE")
    if not isinstance(b["started_at"], str) or (b["completed_at"] is not None and not isinstance(b["completed_at"], str)) or (b["status"] == "complete") != (b["completed_at"] is not None):
        raise CollectorError("BAD_STATE")
    if not isinstance(state["seen_pages"], list) or not all(isinstance(x, str) and ID_RE.fullmatch(x) for x in state["seen_pages"]) or len(set(state["seen_pages"])) != len(state["seen_pages"]):
        raise CollectorError("BAD_STATE")
    if not isinstance(state["seen_urls"], list) or not all(isinstance(x, list) and len(x) == 2 and all(isinstance(y, str) for y in x) for x in state["seen_urls"]):
        raise CollectorError("BAD_STATE")
    if len({tuple(x) for x in state["seen_urls"]}) != len(state["seen_urls"]):
        raise CollectorError("BAD_STATE")
    if not isinstance(state["outbox"], list) or not all(isinstance(x, dict) and set(x) == {"event_id", "item"} for x in state["outbox"]):
        raise CollectorError("BAD_STATE")
    if len({x["event_id"] for x in state["outbox"]}) != len(state["outbox"]):
        raise CollectorError("BAD_STATE")
    for e in state["outbox"]:
        if not isinstance(e["event_id"], str) or not ID_RE.fullmatch(e["event_id"]) or not isinstance(e["item"], dict) or e["item"].get("source_event_id") != e["event_id"]:
            raise CollectorError("BAD_STATE")
    if state["last_success_at"] is not None and not isinstance(state["last_success_at"], str):
        raise CollectorError("BAD_STATE")
    return state


def initial_state(policy: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": SCHEMA, "policy_version": policy["policy_version"], "policy_sha256": policy["policy_sha256"],
            "bootstrap": {"status": "started", "attempts": 1, "started_at": now_iso(), "completed_at": None,
                          "history": [{"number":1,"at":now_iso(),"result":"started"}]},
            "seen_pages": [], "seen_urls": [], "outbox": [], "last_success_at": None}


def write_state(root: Path, state: dict[str, Any]) -> None:
    path = root / STATE_FILE
    safe_file(path, missing_ok=True)
    base = {k: v for k, v in state.items() if k != "integrity_sha256"}
    to_write = {**base, "integrity_sha256": digest(base)}
    temp: Path | None = None
    try:
        fd, name = tempfile.mkstemp(dir=root, prefix=TEMP_PREFIX)
        temp = Path(name)
        with os.fdopen(fd, "wb") as out:
            if os.name != "nt":
                os.fchmod(out.fileno(), 0o600)
            out.write(canonical(to_write) + b"\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        temp = None
        if os.name != "nt":
            dirfd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
    except OSError:
        raise CollectorError("STATE_WRITE_FAILED") from None
    finally:
        if temp and temp.exists():
            # Fail closed next time: don't silently discard interrupted state evidence.
            pass


def read_state(root: Path, policy: dict[str, Any]) -> dict[str, Any] | None:
    if any(p.name.startswith(TEMP_PREFIX) for p in root.iterdir()):
        raise CollectorError("INTERRUPTED_STATE_SAVE")
    path = root / STATE_FILE
    if not path.exists() and not path.is_symlink():
        return None
    return validate_state(load_json(path), policy)


@contextlib.contextmanager
def lock(root: Path) -> Iterator[None]:
    path = root / LOCK_FILE
    safe_file(path, missing_ok=True)
    try:
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except OSError:
        raise CollectorError("LOCK_FAILED") from None
    with os.fdopen(fd, "r+b", buffering=0) as f:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise CollectorError("LOCK_BUSY") from None
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def collect(provider: PageProvider, policy: dict[str, Any], state: dict[str, Any], *, baseline: bool) -> tuple[dict[str, Any], list[str], list[str]]:
    children = validate_parent(provider, policy)
    prior_pages = set(state["seen_pages"])
    prior_urls = {tuple(x) for x in state["seen_urls"]}
    newly: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    pages_seen: set[str] = set()
    urls_seen: set[tuple[str, str]] = set()
    for child in children:
        try:
            urls = validate_child(provider, child)
        except ChildError as e:
            failures.append({"page_id": child["id"], "reason": e.code})
            continue
        pid = child["id"]
        pages_seen.add(pid)
        if not baseline and pid not in prior_pages and policy["conditions"]["new_date_page"]:
            newly.append({"kind": "new_date_page", "page_id": pid, "title": child["title"]})
        for url in urls:
            urls_seen.add((pid, url))
            if not baseline and (pid, url) not in prior_urls and policy["conditions"]["new_url"]:
                newly.append({"kind": "new_url", "page_id": pid, "url": url})
    return {"new": newly, "failures": failures}, sorted(pages_seen), sorted([list(x) for x in urls_seen])


def make_items(events: list[dict[str, Any]], policy: dict[str, Any], stamped: str) -> list[dict[str, Any]]:
    output=[]
    for ev in events:
        rule = ev["kind"]
        identity = [policy["source_id"], rule, ev["page_id"], ev.get("url")]
        event_id = "nj-" + digest(identity)[:40]
        item = {"schema_version":1,"when_fetched":stamped,
                "where":{"source_id":policy["source_id"]},"source_event_id":event_id,
                "who":"synthetic snapshot adapter", "what":"job-page change candidate", 
                "why":rule,"how":"offline local preview; not delivered",
                "payload":{"kind":rule,"page_id":ev["page_id"],"policy_version":policy["policy_version"],
                           "policy_sha256":policy["policy_sha256"],"condition_id":rule}}
        if rule=="new_url":
            item["payload"]["url"] = ev["url"]
        else:
            item["payload"]["date_title"] = ev["title"]
        output.append({"event_id":event_id,"item":item})
    return output


def bootstrap(root: Path, policy: dict[str, Any], provider: PageProvider) -> tuple[int, dict[str, Any]]:
    state = read_state(root, policy)
    if state is None:
        state = initial_state(policy)
        write_state(root, state)
    elif state["bootstrap"]["status"] == "complete":
        raise CollectorError("BOOTSTRAP_ALREADY_COMPLETE")
    else:
        previous = state["bootstrap"]["history"][-1]
        if previous["result"] == "started":
            previous["result"] = "interrupted"
        state["bootstrap"]["attempts"] += 1
        state["bootstrap"]["history"].append({"number":state["bootstrap"]["attempts"], "at":now_iso(), "result":"started"})
        write_state(root, state)
    try:
        result, pages, urls = collect(provider, policy, state, baseline=True)
    except CollectorError as exc:
        state["bootstrap"]["history"][-1]["result"] = "error"
        state["bootstrap"]["history"][-1]["reason"] = exc.code
        write_state(root, state)
        raise
    if result["failures"]:
        state["bootstrap"]["history"][-1]["result"] = "partial"
        state["bootstrap"]["history"][-1]["failed_child_count"] = len(result["failures"])
        write_state(root, state)
        return 2, {"status":"partial","operation":"bootstrap","failed_children":result["failures"],
                   "bootstrap_status":"started","attempts":state["bootstrap"]["attempts"],"last_success_at":None}
    state["seen_pages"] = pages
    state["seen_urls"] = urls
    state["bootstrap"]["status"] = "complete"
    state["bootstrap"]["history"][-1]["result"] = "complete"
    state["bootstrap"]["completed_at"] = now_iso()
    state["last_success_at"] = state["bootstrap"]["completed_at"]
    write_state(root, state)
    return 0, {"status":"ok","operation":"bootstrap","bootstrap_status":"complete",
               "attempts":state["bootstrap"]["attempts"],"baseline_pages":len(pages),
               "baseline_urls":len(urls),"new_events":0,"last_success_at":state["last_success_at"]}


def check(root: Path, policy: dict[str, Any], provider: PageProvider) -> tuple[int, dict[str, Any]]:
    state = read_state(root, policy)
    if state is None or state["bootstrap"]["status"] != "complete":
        raise CollectorError("BOOTSTRAP_NOT_COMPLETE")
    result, pages, urls = collect(provider, policy, state, baseline=False)
    stamped = now_iso()
    proposals = make_items(result["new"], policy, stamped)
    ids = {x["event_id"] for x in state["outbox"]}
    for proposal in proposals:
        if proposal["event_id"] not in ids:
            state["outbox"].append(proposal)
            ids.add(proposal["event_id"])
    state["seen_pages"] = sorted(set(state["seen_pages"]) | set(pages))
    state["seen_urls"] = sorted([list(x) for x in ({tuple(x) for x in state["seen_urls"]} | {tuple(x) for x in urls})])
    if not result["failures"]:
        state["last_success_at"] = stamped
    write_state(root, state)
    status = "partial" if result["failures"] else "ok"
    return 2 if result["failures"] else 0, {"status":status,"operation":"check",
        "new_event_count":len(proposals),"pending_proposal_count":len(state["outbox"]),
        "failed_children":result["failures"],"last_success_at":state["last_success_at"],
        "external_delivery":"NONE","shared_intake_write":False,"notion_connection":"NONE",
        "policy_version":policy["policy_version"],"policy_sha256":policy["policy_sha256"]}


def pending(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    state = read_state(root, policy)
    if state is None or state["bootstrap"]["status"] != "complete":
        raise CollectorError("BOOTSTRAP_NOT_COMPLETE")
    return {"status":"ok","operation":"pending","count":len(state["outbox"]),
            "proposals":state["outbox"],"shared_intake_write":False,"external_delivery":"NONE"}


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Offline synthetic Notion page snapshot to local Shared Intake-compatible proposal; no network")
    parser.add_argument("--policy",type=Path,required=True)
    parser.add_argument("--state-dir",type=Path,required=True)
    cmd=parser.add_subparsers(dest="command",required=True)
    for op in ("bootstrap", "check"):
        p=cmd.add_parser(op)
        p.add_argument("--fixture",type=Path,required=True)
    cmd.add_parser("pending")
    a=parser.parse_args(argv)
    try:
        policy=load_policy(a.policy)
        root=safe_state_dir(a.state_dir)
        fixture=snapshot(a.fixture) if a.command in {"bootstrap", "check"} else None
        with lock(root):
            if a.command=="bootstrap":
                code, result=bootstrap(root,policy,fixture)
            elif a.command=="check":
                code, result=check(root,policy,fixture)
            else:
                code,result=0,pending(root,policy)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        return code
    except CollectorError as e:
        print(json.dumps({"status":"error","error_code":e.code,"items_count":None,"new_events":None},sort_keys=True))
        return 3 if e.code=="LOCK_BUSY" else 1
    except (OSError,UnicodeError,ValueError,OverflowError):
        print(json.dumps({"status":"error","error_code":"UNEXPECTED_LOCAL_ERROR","items_count":None,"new_events":None}))
        return 1


if __name__=="__main__":
    sys.exit(main())
