#!/usr/bin/env python3
"""Offline synthetic Gmail-like record classifier and durable local intake proposals.

This program deliberately has NO Gmail provider, network transport, sender, or
Shared Intake writer. Read-only providers are an interface, not authorization.
SPDX-License-Identifier: GPL-3.0-only
Copyright (C) 2026 Contributors to Agent Ops Script Kit
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import html.parser
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator, Protocol

SCHEMA_VERSION = 1
SOURCE_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SIMPLE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")
ADDRESS = re.compile(r"^[^\s@]{1,128}@[^\s@]{1,255}$")
MAX_POLICY_BYTES = 65536
MAX_ACCOUNTS_BYTES = 65536
MAX_FIXTURE_BYTES = 4 * 1024 * 1024
MAX_STATE_BYTES = 8 * 1024 * 1024
ORDER = ["exclude", "route", "recruitment", "important", "platform"]


class CollectorError(Exception):
    """Validation or local state failure, never interpreted as no messages."""


class LockError(CollectorError):
    pass


class ProviderError(CollectorError):
    pass


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CollectorError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def invalid_constant(value: str) -> None:
    raise CollectorError("INVALID_NUMBER")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(value: Any) -> str:
    return sha_bytes(canonical(value))


def valid_keys(value: Any, keys: set[str], code: str, *, optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CollectorError(code)
    allowed = keys | (optional or set())
    if not keys <= value.keys() or set(value) - allowed:
        raise CollectorError(code)
    return value


def valid_id(value: Any, code: str, regex: re.Pattern[str] = SIMPLE_ID) -> str:
    if type(value) is not str or not regex.fullmatch(value):
        raise CollectorError(code)
    return value


def valid_string(value: Any, code: str, *, max_length: int = 10000) -> str:
    if type(value) is not str or len(value) > max_length:
        raise CollectorError(code)
    return value


def valid_timestamp(value: Any) -> str:
    valid_string(value, "BAD_TIME", max_length=48)
    try:
        timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("no timezone")
    except (ValueError, TypeError) as exc:
        raise CollectorError("BAD_TIME") from exc
    return value


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def safe_path(path: Path, *, exists: bool = True, directory: bool = False) -> Path:
    absolute = Path(os.path.abspath(path))
    for component in reversed((absolute, *absolute.parents)):
        try:
            mode = component.lstat().st_mode
        except FileNotFoundError:
            if component == absolute and not exists:
                continue
            raise CollectorError("INACCESSIBLE_PATH") from None
        except OSError as exc:
            raise CollectorError("INACCESSIBLE_PATH") from exc
        if stat.S_ISLNK(mode):
            raise CollectorError("SYMLINK_PATH")
    if exists:
        if directory and not absolute.is_dir():
            raise CollectorError("INVALID_DIRECTORY")
        if not directory and not absolute.is_file():
            raise CollectorError("INVALID_FILE")
    return absolute


def safe_state_dir(path: Path) -> Path:
    root = safe_path(path, directory=True)
    checkout = Path(__file__).resolve().parents[1]
    if root == checkout or checkout in root.parents:
        raise CollectorError("STATE_INSIDE_CHECKOUT")
    try:
        if any(p.name.startswith(".gmail-collector-temp-") for p in root.iterdir()):
            raise CollectorError("INTERRUPTED_STATE_WRITE")
    except OSError as exc:
        raise CollectorError("INACCESSIBLE_STATE_DIR") from exc
    return root


def read_json(path: Path, max_size: int) -> tuple[Any, str]:
    target = safe_path(path)
    try:
        if target.stat().st_size > max_size:
            raise CollectorError("INPUT_TOO_LARGE")
        raw = target.read_bytes()
    except OSError as exc:
        raise CollectorError("INPUT_READ_FAILED") from exc
    if not raw:
        raise CollectorError("EMPTY_INPUT")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise CollectorError("INVALID_JSON") from exc
    return data, sha_bytes(raw)


def terms(value: Any, code: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 40:
        raise CollectorError(code)
    output = []
    for part in value:
        if type(part) is not str or not part.strip() or len(part) > 140:
            raise CollectorError(code)
        output.append(part.casefold())
    if len(set(output)) != len(output):
        raise CollectorError(code)
    return output


def rule(value: Any, keys: set[str]) -> dict[str, Any]:
    obj = valid_keys(value, keys | {"id"}, "BAD_POLICY_RULE")
    valid_id(obj["id"], "BAD_POLICY_RULE")
    return obj


def load_policy(path: Path) -> dict[str, Any]:
    raw, checksum = read_json(path, MAX_POLICY_BYTES)
    required = {"schema_version", "policy_version", "source_id", "account_roles",
                "max_pages_per_account", "max_messages_per_account", "classification_order",
                "exclude", "routes", "recruitment", "importance", "platform"}
    p = valid_keys(raw, required, "BAD_POLICY")
    if type(p["schema_version"]) is not int or p["schema_version"] != 1:
        raise CollectorError("BAD_POLICY_VERSION")
    valid_id(p["policy_version"], "BAD_POLICY_VERSION")
    valid_id(p["source_id"], "BAD_POLICY", SOURCE_ID)
    for field, upper in (("max_pages_per_account", 1000), ("max_messages_per_account", 50000)):
        v = p[field]
        if type(v) is not int or not 1 <= v <= upper:
            raise CollectorError("BAD_POLICY_LIMIT")
    if type(p["classification_order"]) is not list or p["classification_order"] != ORDER:
        raise CollectorError("UNKNOWN_CONDITION_ID")
    roles = p["account_roles"]
    if not isinstance(roles, list) or not 1 <= len(roles) <= 8 or len(set(map(str, roles))) != len(roles):
        raise CollectorError("BAD_ACCOUNT_ROLES")
    for role in roles:
        valid_id(role, "BAD_ACCOUNT_ROLES", SOURCE_ID)
    ids: list[str] = []
    exclusions = rule(p["exclude"], {"terms"})
    exclusions["terms"] = terms(exclusions["terms"], "BAD_POLICY_TERMS")
    ids.append(exclusions["id"])
    if not isinstance(p["routes"], list) or len(p["routes"]) != len(roles):
        raise CollectorError("BAD_POLICY_ROUTE")
    route_roles: set[str] = set()
    for obj in p["routes"]:
        r = rule(obj, {"account_role", "destination"})
        valid_id(r["account_role"], "BAD_POLICY_ROUTE", SOURCE_ID)
        valid_id(r["destination"], "BAD_POLICY_ROUTE", SOURCE_ID)
        if r["account_role"] not in roles or r["account_role"] in route_roles:
            raise CollectorError("BAD_POLICY_ROUTE")
        route_roles.add(r["account_role"])
        ids.append(r["id"])
    if route_roles != set(roles):
        raise CollectorError("BAD_POLICY_ROUTE")
    recruitment = rule(p["recruitment"], {"terms"})
    recruitment["terms"] = terms(recruitment["terms"], "BAD_POLICY_TERMS")
    ids.append(recruitment["id"])
    importance = rule(p["importance"], {"strong", "weak", "negative", "action", "self_target", "date", "promotion"})
    for field in ("strong", "weak", "negative", "action", "self_target", "date", "promotion"):
        importance[field] = terms(importance[field], "BAD_POLICY_TERMS")
    ids.append(importance["id"])
    platform = rule(p["platform"], {"terms"})
    platform["terms"] = terms(platform["terms"], "BAD_POLICY_TERMS")
    ids.append(platform["id"])
    if len(ids) != len(set(ids)):
        raise CollectorError("DUPLICATE_CONDITION_ID")
    p["policy_sha256"] = checksum
    return p


def load_accounts(path: Path, policy: dict[str, Any]) -> tuple[dict[str, Any], str]:
    raw, checksum = read_json(path, MAX_ACCOUNTS_BYTES)
    config = valid_keys(raw, {"schema_version", "accounts"}, "BAD_ACCOUNT_CONFIG")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise CollectorError("BAD_ACCOUNT_CONFIG")
    accounts = config["accounts"]
    if not isinstance(accounts, list) or len(accounts) != len(policy["account_roles"]):
        raise CollectorError("BAD_ACCOUNT_COUNT")
    ids, addresses, roles = set(), set(), set()
    by_id = {}
    for entry in accounts:
        a = valid_keys(entry, {"account_id", "role", "address"}, "BAD_ACCOUNT_CONFIG")
        aid = valid_id(a["account_id"], "BAD_ACCOUNT_ID", SOURCE_ID)
        role_name = valid_id(a["role"], "BAD_ACCOUNT_ROLE", SOURCE_ID)
        addr = a["address"]
        if type(addr) is not str or not ADDRESS.fullmatch(addr):
            raise CollectorError("BAD_ACCOUNT_ADDRESS")
        folded = addr.casefold()
        if aid in ids or folded in addresses or role_name in roles:
            raise CollectorError("DUPLICATE_ACCOUNT")
        ids.add(aid)
        addresses.add(folded)
        roles.add(role_name)
        by_id[aid] = dict(a)
    if roles != set(policy["account_roles"]):
        raise CollectorError("BAD_ACCOUNT_ROLES")
    return by_id, checksum


class MailProvider(Protocol):
    """Read-only boundary. Public kit does not ship a live provider."""
    def list_page(self, account_id: str, token: str | None) -> Any: ...
    def get_message(self, account_id: str, message_id: str) -> Any: ...


class FixtureProvider:
    """Entirely local synthetic fixture. No network, tokens or external calls."""
    def __init__(self, raw: Any):
        obj = valid_keys(raw, {"schema_version", "accounts"}, "BAD_FIXTURE")
        if type(obj["schema_version"]) is not int or obj["schema_version"] != 1:
            raise CollectorError("BAD_FIXTURE")
        if not isinstance(obj["accounts"], dict):
            raise CollectorError("BAD_FIXTURE")
        self.accounts = obj["accounts"]

    def _account(self, aid: str) -> dict[str, Any]:
        obj = self.accounts.get(aid)
        if not isinstance(obj, dict):
            raise ProviderError("ACCOUNT_FETCH_FAILED")
        if obj.get("fetch_error") is not None:
            raise ProviderError("ACCOUNT_FETCH_FAILED")
        return obj

    def list_page(self, account_id: str, token: str | None) -> Any:
        obj = self._account(account_id)
        pages = obj.get("pages")
        if not isinstance(pages, list):
            raise ProviderError("INVALID_PAGE_RESPONSE")
        matches = [p for p in pages if isinstance(p, dict) and p.get("token", object()) == token]
        if len(matches) != 1:
            raise ProviderError("INVALID_PAGE_RESPONSE")
        return matches[0]

    def get_message(self, account_id: str, message_id: str) -> Any:
        obj = self._account(account_id)
        items = obj.get("messages")
        if not isinstance(items, dict) or message_id not in items:
            raise ProviderError("MESSAGE_FETCH_FAILED")
        return items[message_id]


def fixture(path: Path) -> FixtureProvider:
    return FixtureProvider(read_json(path, MAX_FIXTURE_BYTES)[0])


class VisibleText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def message_text(msg: dict[str, Any]) -> str:
    viewer = VisibleText()
    if msg["body_html"]:
        viewer.feed(msg["body_html"])
    return " ".join((msg["subject"], msg["body_text"], " ".join(viewer.parts))).casefold()


def check_message(raw: Any, expected_id: str) -> dict[str, Any]:
    mandatory = {"id", "thread_id", "received_at", "from", "to", "subject", "body_text", "body_html", "attachments"}
    msg = valid_keys(raw, mandatory, "INVALID_MESSAGE")
    if valid_id(msg["id"], "INVALID_MESSAGE_ID") != expected_id:
        raise CollectorError("INVALID_MESSAGE_ID")
    valid_id(msg["thread_id"], "INVALID_THREAD_ID")
    valid_timestamp(msg["received_at"])
    for f in ("from", "to"):
        if type(msg[f]) is not str or not ADDRESS.fullmatch(msg[f]):
            raise CollectorError("INVALID_MESSAGE_ADDRESS")
    for f in ("subject", "body_text", "body_html"):
        valid_string(msg[f], "INVALID_MESSAGE_TEXT", max_length=30000)
    if not isinstance(msg["attachments"], list) or len(msg["attachments"]) > 100:
        raise CollectorError("INVALID_MESSAGE_ATTACHMENTS")
    # No attachment object is opened, traversed, or stored.
    return msg


def matched(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def classify(msg: dict[str, Any], policy: dict[str, Any], role: str) -> dict[str, Any]:
    content = message_text(msg)
    if matched(content, policy["exclude"]["terms"]):
        return {"category": "excluded", "important": False, "route": None,
                "condition_id": policy["exclude"]["id"]}
    route = next(x for x in policy["routes"] if x["account_role"] == role)
    importance = policy["importance"]
    strong = matched(content, importance["strong"])
    weak = matched(content, importance["weak"])
    negative = matched(content, importance["negative"])
    action = matched(content, importance["action"])
    self_target = matched(content, importance["self_target"])
    deadline = matched(content, importance["date"])
    # Weak words plus promotional deadlines are not automatically important.
    strong_context = negative or sum((action, self_target, deadline)) >= 2
    important = strong or (weak and strong_context) or (action and (negative or self_target))
    if matched(content, importance["promotion"]) and not (strong or negative or self_target):
        important = False
    if matched(content, policy["recruitment"]["terms"]):
        category, condition_id = "recruitment", policy["recruitment"]["id"]
    elif important:
        category, condition_id = "important", importance["id"]
    elif matched(content, policy["platform"]["terms"]):
        category, condition_id = "platform", policy["platform"]["id"]
    else:
        category, condition_id = "other", None
    return {"category": category, "important": important,
            "route": route["destination"], "routing_condition_id": route["id"],
            "condition_id": condition_id}


def list_account(provider: MailProvider, aid: str, policy: dict[str, Any]) -> tuple[list[str], bool, str | None, int]:
    result: list[str] = []
    page_token: str | None = None
    visited: set[str | None] = set()
    bad_ids = 0
    limit_pages = policy["max_pages_per_account"]
    limit_msgs = policy["max_messages_per_account"]
    for _ in range(limit_pages):
        if page_token in visited:
            return result, False, "PAGINATION_LOOP", bad_ids
        visited.add(page_token)
        try:
            page = provider.list_page(aid, page_token)
        except ProviderError as exc:
            return result, False, str(exc), bad_ids
        if not isinstance(page, dict) or set(page) != {"token", "next", "message_ids"}:
            return result, False, "INVALID_PAGE_RESPONSE", bad_ids
        if page["token"] != page_token or not isinstance(page["message_ids"], list):
            return result, False, "INVALID_PAGE_RESPONSE", bad_ids
        next_token = page["next"]
        if next_token is not None:
            try:
                valid_id(next_token, "INVALID_PAGE_TOKEN")
            except CollectorError:
                return result, False, "INVALID_PAGE_TOKEN", bad_ids
        for mid in page["message_ids"]:
            try:
                valid_id(mid, "INVALID_MESSAGE_ID")
            except CollectorError:
                bad_ids += 1
                continue
            if mid not in result:
                result.append(mid)
            if len(result) > limit_msgs:
                # The page was only partially consumed: do not call this complete.
                return result[:limit_msgs], False, "MESSAGE_LIMIT_REACHED", bad_ids
        if next_token is None:
            return result, True, None, bad_ids
        page_token = next_token
    return result, False, "PAGE_LIMIT_REACHED", bad_ids


def initial_state(policy: dict[str, Any], accounts_sha: str) -> dict[str, Any]:
    return {"schema_version":1, "policy_version":policy["policy_version"],
            "policy_sha256":policy["policy_sha256"],"accounts_sha256":accounts_sha,
            "seen":[],"outbox":[],"last_success_at":None,"attempt_count":0,
            "last_attempt":None}


def state_hash(value: dict[str, Any]) -> str:
    return digest({k:v for k,v in value.items() if k != "integrity_sha256"})


def validate_state(raw: Any, policy: dict[str, Any], accounts_sha: str) -> dict[str, Any]:
    keys = {"schema_version", "policy_version", "policy_sha256", "accounts_sha256", "seen",
            "outbox", "last_success_at", "attempt_count", "last_attempt", "integrity_sha256"}
    state = valid_keys(raw, keys, "BAD_STATE")
    if type(state["schema_version"]) is not int or state["schema_version"] != 1:
        raise CollectorError("BAD_STATE")
    if (state["policy_version"],state["policy_sha256"],state["accounts_sha256"]) != (
        policy["policy_version"],policy["policy_sha256"],accounts_sha):
        raise CollectorError("CONFIG_MISMATCH")
    if type(state["integrity_sha256"]) is not str or state["integrity_sha256"] != state_hash(state):
        raise CollectorError("BAD_STATE_HASH")
    seen = state["seen"]
    if not isinstance(seen, list) or any(type(x) is not str or not re.fullmatch(r"[a-f0-9]{64}",x) for x in seen):
        raise CollectorError("BAD_STATE")
    if len(seen) != len(set(seen)) or seen != sorted(seen):
        raise CollectorError("BAD_STATE")
    outbox = state["outbox"]
    if not isinstance(outbox, list) or len(outbox) > 30000:
        raise CollectorError("BAD_STATE")
    event_ids = set()
    for entry in outbox:
        valid_keys(entry, {"event_id", "item"}, "BAD_STATE")
        valid_id(entry["event_id"], "BAD_STATE")
        if entry["event_id"] in event_ids or not isinstance(entry["item"], dict):
            raise CollectorError("BAD_STATE")
        if entry["item"].get("source_event_id") != entry["event_id"]:
            raise CollectorError("BAD_STATE")
        event_ids.add(entry["event_id"])
    if state["last_success_at"] is not None:
        valid_timestamp(state["last_success_at"])
    if type(state["attempt_count"]) is not int or state["attempt_count"] < 0:
        raise CollectorError("BAD_STATE")
    if state["last_attempt"] is not None:
        val = valid_keys(state["last_attempt"],{"at","status","failed_accounts","invalid_messages"},"BAD_STATE")
        valid_timestamp(val["at"])
        if val["status"] not in {"ok","partial","error"} or type(val["failed_accounts"]) is not int or type(val["invalid_messages"]) is not int:
            raise CollectorError("BAD_STATE")
    return state


def state_file(root: Path) -> Path:
    return root / "gmail-collector-state.json"


def read_state(root: Path, policy: dict[str, Any], accounts_sha: str) -> dict[str, Any]:
    file = state_file(root)
    if not file.exists() and not file.is_symlink():
        return initial_state(policy, accounts_sha)
    data,_ = read_json(file, MAX_STATE_BYTES)
    return validate_state(data, policy, accounts_sha)


def save_state(root: Path, state: dict[str, Any]) -> None:
    target = state_file(root)
    safe_path(target,exists=False) if not target.exists() else safe_path(target)
    body = dict(state)
    body["integrity_sha256"] = state_hash(body)
    data = canonical(body) + b"\n"
    if len(data) > MAX_STATE_BYTES:
        raise CollectorError("STATE_TOO_LARGE")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb",dir=root,prefix=".gmail-collector-temp-",delete=False) as f:
            temporary = Path(f.name)
            if os.name != "nt":
                os.fchmod(f.fileno(),0o600)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary,target)
        temporary=None
        if os.name != "nt":
            directory_fd=os.open(root,os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        raise CollectorError("STATE_WRITE_FAILED") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


@contextlib.contextmanager
def locked(root: Path) -> Iterator[None]:
    target = root / ".gmail-collector.lock"
    if target.exists() or target.is_symlink():
        safe_path(target)
    fd=None
    try:
        fd=os.open(target,os.O_RDWR | os.O_CREAT | getattr(os,"O_NOFOLLOW",0),0o600)
        if os.name == "nt":
            import msvcrt
            os.lseek(fd,0,os.SEEK_SET)
            try:
                msvcrt.locking(fd,msvcrt.LK_NBLCK,1)
            except OSError as exc:
                raise LockError("LOCK_UNAVAILABLE") from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LockError("LOCK_UNAVAILABLE") from exc
        yield
    except OSError as exc:
        raise CollectorError("LOCK_FAILED") from exc
    finally:
        if fd is not None:
            if os.name == "nt":
                try:
                    import msvcrt
                    os.lseek(fd,0,os.SEEK_SET)
                    msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
                except OSError:
                    pass
            else:
                try:
                    import fcntl
                    fcntl.flock(fd,fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(fd)


def make_proposal(aid: str, mid: str, role: str, result: dict[str, Any],
                  policy: dict[str, Any], accounts_sha: str, timestamp: str) -> dict[str, Any]:
    ref = digest([policy["source_id"],aid,mid])
    event_id = "mail-" + ref[:48]
    item = {
      "schema_version":1,
      "when_fetched":timestamp,
      "where":{"source_id":policy["source_id"]},
      "source_event_id":event_id,
      "who":"offline synthetic mail provider",
      "what":"synthetic email classification candidate",
      "why":"mechanical policy match; not a human decision",
      "how":"local preview only; not delivered",
      "payload":{
        "kind":"synthetic_mail_candidate","message_ref_sha256":ref,
        "account_role":role,"route":result["route"],
        "category":result["category"],"important_flag":result["important"],
        "condition_id":result["condition_id"],
        "routing_condition_id":result["routing_condition_id"],
        "policy_version":policy["policy_version"],
        "policy_sha256":policy["policy_sha256"],
        "account_config_sha256":accounts_sha,
        "external_delivery":"NONE"
      }
    }
    return {"event_id":event_id,"item":item}


def check(policy: dict[str, Any], accounts: dict[str, Any], accounts_sha: str,
          provider: MailProvider, state: dict[str, Any]) -> tuple[int,dict[str, Any],bool]:
    seen = set(state["seen"])
    outbox_ids = {x["event_id"] for x in state["outbox"]}
    proposals = []
    excluded = 0
    ignored = 0
    invalid = 0
    account_ok = 0
    account_partial = 0
    account_fail = 0
    failures: list[dict[str, str]] = []
    timestamp = now_iso()
    for aid,acct in sorted(accounts.items()):
        ids,complete,error,bad_ids = list_account(provider,aid,policy)
        invalid += bad_ids
        bad_msg = bad_ids
        success_msg = 0
        if error is not None:
            failures.append({"account_role":acct["role"],"code":error})
        for mid in ids:
            key = digest([aid,mid])
            if key in seen:
                continue
            try:
                raw = provider.get_message(aid,mid)
                msg = check_message(raw,mid)
            except (ProviderError,CollectorError):
                invalid += 1
                bad_msg += 1
                continue
            result = classify(msg,policy,acct["role"])
            seen.add(key)
            success_msg += 1
            if result["category"] == "excluded":
                excluded += 1
            elif result["category"] == "other":
                ignored += 1
            else:
                proposal = make_proposal(aid,mid,acct["role"],result,policy,accounts_sha,timestamp)
                if proposal["event_id"] not in outbox_ids:
                    proposals.append(proposal)
                    outbox_ids.add(proposal["event_id"])
        if complete and bad_msg == 0:
            account_ok += 1
        elif not complete and success_msg == 0 and bad_msg == 0:
            account_fail += 1
        else:
            account_partial += 1
            if bad_msg:
                failures.append({"account_role":acct["role"],"code":"INVALID_MESSAGES"})
        # Missing/incomplete page never counts as a complete success.
    if account_ok == 0 and account_partial == 0:
        status,exit_code = "error",1
        new_count: int | None = None
        # No account yielded trustworthy data; do not modify state or success time.
        return exit_code,{"status":status,"operation":"check","new_event_count":new_count,
             "pending_proposal_count":None,"accounts_complete":0,"accounts_partial":0,
             "accounts_failed":account_fail,"invalid_messages":invalid,
             "failures":failures,"last_success_at":state["last_success_at"],
             "gmail_connection":"NONE","shared_intake_write":False,"external_delivery":"NONE",
             "policy_version":policy["policy_version"],"policy_sha256":policy["policy_sha256"]},False
    status = "ok" if account_partial == 0 and account_fail == 0 else "partial"
    exit_code = 0 if status == "ok" else 2
    updated = dict(state)
    updated["seen"] = sorted(seen)
    updated["outbox"] = state["outbox"] + proposals
    updated["attempt_count"] += 1
    updated["last_attempt"] = {"at":timestamp,"status":status,"failed_accounts":account_fail,
                                "invalid_messages":invalid}
    if status == "ok":
        updated["last_success_at"] = timestamp
    # Caller persists updated state as a single transaction before returning success.
    state.update(updated)
    return exit_code,{"status":status,"operation":"check","new_event_count":len(proposals),
         "pending_proposal_count":len(updated["outbox"]),"accounts_complete":account_ok,
         "accounts_partial":account_partial,"accounts_failed":account_fail,
         "invalid_messages":invalid,"excluded_messages":excluded,"unmatched_messages":ignored,
         "failures":failures,"last_success_at":updated["last_success_at"],
         "gmail_connection":"NONE","shared_intake_write":False,"external_delivery":"NONE",
         "policy_version":policy["policy_version"],"policy_sha256":policy["policy_sha256"],
         "account_config_sha256":accounts_sha},True


def pending(state: dict[str, Any]) -> dict[str, Any]:
    return {"status":"ok","operation":"pending", "count":len(state["outbox"]),
            "proposals":state["outbox"],"gmail_connection":"NONE",
            "shared_intake_write":False,"external_delivery":"NONE"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OFFLINE synthetic Gmail-like fixture classifier; no network, Gmail or send")
    parser.add_argument("--policy",required=True,type=Path)
    parser.add_argument("--accounts",required=True,type=Path)
    parser.add_argument("--state-dir",required=True,type=Path)
    sub = parser.add_subparsers(dest="command",required=True)
    cmd = sub.add_parser("check",help="Read an offline fixture; classify and save local proposals only")
    cmd.add_argument("--fixture",required=True,type=Path)
    sub.add_parser("pending",help="Print locally persisted, unshipped proposals")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy)
        accounts,accounts_sha = load_accounts(args.accounts,policy)
        root = safe_state_dir(args.state_dir)
        with locked(root):
            state = read_state(root,policy,accounts_sha)
            if args.command == "check":
                provider = fixture(args.fixture)
                status,report,modified = check(policy,accounts,accounts_sha,provider,state)
                if modified:
                    save_state(root,state)
                print(json.dumps(report,ensure_ascii=False,sort_keys=True))
                return status
            report = pending(state)
            print(json.dumps(report,ensure_ascii=False,sort_keys=True))
            return 0
    except LockError as exc:
        print(json.dumps({"status":"error","code":str(exc),"new_event_count":None,
              "gmail_connection":"NONE","shared_intake_write":False}),file=sys.stdout)
        return 3
    except (CollectorError,OSError,ValueError,TypeError) as exc:
        code = str(exc) if isinstance(exc,CollectorError) else "UNEXPECTED_IO_OR_DATA_ERROR"
        print(json.dumps({"status":"error","code":code,"new_event_count":None,
              "gmail_connection":"NONE","shared_intake_write":False}),file=sys.stdout)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
