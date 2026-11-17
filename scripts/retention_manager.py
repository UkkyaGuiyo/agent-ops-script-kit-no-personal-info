#!/usr/bin/env python3
"""Demo-scoped, reversible staging of explicitly tagged synthetic files.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only

No purge/delete or production-file operations. Demo staging needs --apply.
State and manifests stay inside a caller-owned temporary synthetic sandbox.
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
import uuid

if os.name == "posix":
    import fcntl
from pathlib import Path
from typing import Any

DAY_NS = 86_400_000_000_000
RECORD = '.retention_records.json'
MARKER = '.retention_demo.json'
TRASH = '.trash'
AUDIT = 'events.jsonl'
LOCK = '.retention_demo.lock'
MAX_RECORD_BYTES = 1_000_000
MAX_MANIFEST_BYTES = 20_000
SAFE_NAME = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
ENTRY_ID = re.compile(r'^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{32}$')
EXCLUDED = frozenset({RECORD, MARKER, TRASH, LOCK, '.git', 'node_modules', 'venv', '.venv'})


class RetentionError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise RetentionError('DUPLICATE_KEY')
        result[name] = value
    return result


def reject_const(_value: str) -> None:
    raise RetentionError('NONSTANDARD_NUMBER')


def read_json(path: Path, max_bytes: int) -> Any:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                raise RetentionError('INVALID_FILE_TYPE_OR_SIZE')
            with os.fdopen(fd, 'r', encoding='utf-8') as handle:
                fd = -1
                text = handle.read(max_bytes + 1)
            if len(text.encode('utf-8')) > max_bytes:
                raise RetentionError('FILE_TOO_LARGE')
            return json.loads(text, object_pairs_hook=no_dupes, parse_constant=reject_const)
        finally:
            if fd >= 0:
                os.close(fd)
    except RetentionError:
        raise
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        raise RetentionError('INVALID_OR_INACCESSIBLE_JSON') from exc


def atomic_json(path: Path, obj: dict[str, Any]) -> None:
    text = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n'
    temp = path.with_name('.retention-temp-' + uuid.uuid4().hex)
    descriptor = None
    try:
        descriptor = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            descriptor = None
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        sync_dir(path.parent)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temp.exists():
            temp.unlink()


def sync_dir(path: Path) -> None:
    if os.name != 'posix':
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def real_dir(path: Path) -> Path:
    root = Path(os.path.abspath(path))
    for p in reversed((root, *root.parents)):
        try:
            if stat.S_ISLNK(p.lstat().st_mode):
                raise RetentionError('SYMLINK_PATH')
        except OSError as exc:
            raise RetentionError('INACCESSIBLE_ROOT') from exc
    if not stat.S_ISDIR(root.lstat().st_mode):
        raise RetentionError('NOT_DIRECTORY')
    return root


@contextlib.contextmanager
def demo_lock(root: Path):
    """Advisory, nonblocking same-host lock for demonstration writes only."""
    if os.name != 'posix':
        raise RetentionError('POSIX_DEMO_ONLY')
    fd = -1
    try:
        fd = os.open(root / LOCK, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RetentionError('INVALID_DEMO_LOCK')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RetentionError('DEMO_LOCK_BUSY') from exc
        yield
    except RetentionError:
        raise
    except OSError as exc:
        raise RetentionError('DEMO_LOCK_ERROR') from exc
    finally:
        if fd >= 0:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def demo_marker(root: Path) -> dict[str, Any]:
    temp_root = real_dir(Path(tempfile.gettempdir()))
    if root == temp_root or temp_root not in root.parents:
        raise RetentionError('DEMO_ROOT_MUST_BE_INSIDE_OS_TEMP')
    marker = read_json(root / MARKER, 4096)
    if not isinstance(marker, dict) or set(marker) != {'schema_version', 'synthetic', 'sandbox_id'}:
        raise RetentionError('DEMO_MARKER_REQUIRED')
    if type(marker['schema_version']) is not int or marker['schema_version'] != 1 or marker['synthetic'] is not True:
        raise RetentionError('DEMO_MARKER_REQUIRED')
    if not isinstance(marker['sandbox_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', marker['sandbox_id']):
        raise RetentionError('DEMO_MARKER_REQUIRED')
    return marker


def valid_filename(raw: Any) -> bool:
    return (isinstance(raw, str) and raw not in EXCLUDED and bool(SAFE_NAME.fullmatch(raw))
            and raw not in ('.', '..') and not raw.startswith('.retention-temp-'))


def safe_file(root: Path, name: str) -> os.stat_result:
    try:
        info = (root / name).lstat()
    except FileNotFoundError as exc:
        raise RetentionError('MISSING_REGISTERED_FILE') from exc
    except OSError as exc:
        raise RetentionError('INACCESSIBLE_REGISTERED_FILE') from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RetentionError('NOT_SINGLE_LINK_REGULAR_FILE')
    return info


def checksum(path: Path) -> tuple[str, int]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise RetentionError('NOT_SINGLE_LINK_REGULAR_FILE')
            h = hashlib.sha256()
            length = 0
            with os.fdopen(descriptor, 'rb') as stream:
                descriptor = -1
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(chunk)
                    length += len(chunk)
            return h.hexdigest(), length
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except RetentionError:
        raise
    except OSError as exc:
        raise RetentionError('FILE_READ_FAILURE') from exc


def records(root: Path) -> list[dict[str, Any]]:
    raw = read_json(root / RECORD, MAX_RECORD_BYTES)
    if not isinstance(raw, dict) or set(raw) not in ({'entries'}, {'version', 'entries'}):
        raise RetentionError('BAD_RETENTION_RECORD')
    if 'version' in raw and (type(raw['version']) is not int or raw['version'] != 1):
        raise RetentionError('BAD_RETENTION_RECORD')
    if not isinstance(raw['entries'], list):
        raise RetentionError('BAD_RETENTION_RECORD')
    seen: set[str] = set()
    out = []
    for index, entry in enumerate(raw['entries']):
        if not isinstance(entry, dict) or set(entry) != {'path', 'class'}:
            out.append({'index': index, 'name': None, 'tag': None, 'error': 'MALFORMED_ENTRY'})
            continue
        name, tag = entry['path'], entry['class']
        if isinstance(name, str) and name in seen:
            raise RetentionError('DUPLICATE_RECORDED_PATH')
        if isinstance(name, str):
            seen.add(name)
        out.append({'index': index, 'name': name if valid_filename(name) else None,
                    'tag': tag if isinstance(tag, str) else None,
                    'error': None if valid_filename(name) else 'UNSAFE_OR_UNSUPPORTED_PATH'})
    return out


def as_of_ns(value: str | None) -> tuple[int, str]:
    if value is None:
        now = dt.datetime.now(dt.timezone.utc)
    else:
        try:
            now = dt.datetime.fromisoformat(value)
        except (TypeError, ValueError) as exc:
            raise RetentionError('BAD_AS_OF') from exc
        if now.tzinfo is None or now.utcoffset() is None:
            raise RetentionError('BAD_AS_OF')
        now = now.astimezone(dt.timezone.utc)
    epoch = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    difference = now - epoch
    ns = ((difference.days * 86400 + difference.seconds) * 1_000_000 + difference.microseconds) * 1000
    return ns, now.isoformat()


def evaluate(root: Path, rows: list[dict[str, Any]], now_ns: int, days: int) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        obj = {'index': row['index'], 'name': row['name'], 'tag': row['tag'],
               'decision': 'hold', 'reason': row['error'], 'age_seconds': None}
        if row['error']:
            result.append(obj)
            continue
        name, tag = row['name'], row['tag']
        if tag not in ('disposable', 'permanent'):
            obj['reason'] = 'UNKNOWN_TAG'
            result.append(obj)
            continue
        try:
            info = safe_file(root, name)
        except RetentionError as exc:
            obj['reason'] = exc.code
            result.append(obj)
            continue
        if tag == 'permanent':
            obj.update(decision='excluded', reason='PERMANENT_TAG')
        elif now_ns < info.st_mtime_ns:
            obj['reason'] = 'FUTURE_MTIME'
        else:
            elapsed = now_ns - info.st_mtime_ns
            obj['age_seconds'] = elapsed // 1_000_000_000
            obj.update(decision='candidate' if elapsed >= days * DAY_NS else 'not_due',
                       reason='DISPOSABLE_DUE' if elapsed >= days * DAY_NS else 'DISPOSABLE_NOT_DUE')
        result.append(obj)
    return result


def preflight_trash(root: Path) -> None:
    path = root / TRASH
    if not path.exists():
        return
    if not stat.S_ISDIR(path.lstat().st_mode):
        raise RetentionError('INVALID_TRASH_DIR')
    for child in path.iterdir():
        if child.name == AUDIT:
            if not stat.S_ISREG(child.lstat().st_mode):
                raise RetentionError('INVALID_AUDIT')
            continue
        if child.name.startswith('.retention-temp-'):
            raise RetentionError('ORPHAN_TEMPORARY_FILE')
        if not stat.S_ISDIR(child.lstat().st_mode) or not ENTRY_ID.fullmatch(child.name):
            raise RetentionError('UNRECOGNIZED_TRASH_ENTRY')
        manifest = read_json(child / 'manifest.json', MAX_MANIFEST_BYTES)
        if not isinstance(manifest, dict) or manifest.get('phase') not in ('staged', 'restored'):
            raise RetentionError('INCOMPLETE_STAGING_REQUIRES_MANUAL_REVIEW')
        allowed = {'schema_version', 'entry_id', 'sandbox_id', 'name', 'sha256', 'size_bytes', 'mtime_ns', 'staged_at_utc', 'phase'}
        if set(manifest) != allowed or manifest.get('entry_id') != child.name:
            raise RetentionError('BAD_STAGING_MANIFEST')
        if not valid_filename(manifest['name']) or type(manifest['size_bytes']) is not int or type(manifest['mtime_ns']) is not int:
            raise RetentionError('BAD_STAGING_MANIFEST')
        payload = child / 'payload'
        if manifest['phase'] == 'staged':
            if not payload.exists() or not stat.S_ISREG(payload.lstat().st_mode):
                raise RetentionError('STAGED_PAYLOAD_MISSING')
        elif payload.exists() or payload.is_symlink():
            raise RetentionError('RESTORED_ENTRY_HAS_PAYLOAD')


def report(root: Path, days: int, at: str | None) -> dict[str, Any]:
    if type(days) is not int or days < 0 or days > 365_000:
        raise RetentionError('BAD_AGE_DAYS')
    now_ns, stamp = as_of_ns(at)
    rows = records(root)
    checks = evaluate(root, rows, now_ns, days)
    counts = {name: sum(x['decision'] == name for x in checks) for name in ('candidate','not_due','excluded','hold')}
    return {'status': 'partial' if counts['hold'] else 'ok', 'operation': 'preview', 'dry_run': True,
            'as_of_utc': stamp, 'age_days': days, 'counts': counts, 'items': checks,
            'records_changed': 0, 'unregistered_files_scanned': False,
            'trash_move_available': False, 'purge_available': False, 'restore_available': False}


def append_audit(root: Path, event: dict[str, Any]) -> None:
    destination = root / TRASH / AUDIT
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            with os.fdopen(fd, 'a', encoding='utf-8') as stream:
                fd = -1
                stream.write(json.dumps(event, sort_keys=True) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            if fd >= 0:
                os.close(fd)
    except OSError as exc:
        raise RetentionError('AUDIT_APPEND_FAILED') from exc


def _stage_unlocked(root: Path, days: int, at: str | None, apply: bool) -> dict[str, Any]:
    marker = demo_marker(root)
    preflight_trash(root)
    preview = report(root, days, at)
    if preview['counts']['hold']:
        return {**preview, 'operation':'stage', 'status':'partial', 'staged_count':0,
                'dry_run':True, 'reason':'HOLD_BLOCKS_STAGING'}
    if not apply:
        return {**preview, 'operation':'stage', 'staged_count':0, 'reason':'APPLY_REQUIRED'}
    if os.name != 'posix':
        raise RetentionError('STAGING_POSIX_DEMO_ONLY')
    candidates = [x for x in preview['items'] if x['decision']=='candidate']
    if not candidates:
        return {**preview, 'operation':'stage', 'staged_count':0, 'reason':'NO_CANDIDATES'}
    trash = root / TRASH
    trash.mkdir(mode=0o700, exist_ok=True)
    staged = []
    for item in candidates:
        name = item['name']
        before = safe_file(root, name)
        now_ns,_=as_of_ns(at)
        if now_ns < before.st_mtime_ns or now_ns-before.st_mtime_ns < days * DAY_NS:
            raise RetentionError('FILE_CHANGED_SINCE_PREVIEW')
        digest,size = checksum(root / name)
        after = safe_file(root, name)
        if (before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size)!=(after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size) or size != after.st_size:
            raise RetentionError('FILE_CHANGED_DURING_HASH')
        staged_stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        entry_id=staged_stamp+'-'+uuid.uuid4().hex
        folder=trash / entry_id
        folder.mkdir(mode=0o700)
        manifest={'schema_version':1,'entry_id':entry_id,'sandbox_id':marker['sandbox_id'],
                  'name':name,'sha256':digest,'size_bytes':size,'mtime_ns':before.st_mtime_ns,
                  'staged_at_utc':staged_stamp,'phase':'prepared'}
        atomic_json(folder/'manifest.json',manifest)
        # Check identity at the last checkpoint; kernel-level races remain out of scope.
        final = safe_file(root,name)
        if (final.st_dev,final.st_ino,final.st_mtime_ns,final.st_size)!=(after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size):
            raise RetentionError('FILE_CHANGED_BEFORE_MOVE')
        os.replace(root/name, folder/'payload')
        sync_dir(root)
        sync_dir(folder)
        actual,size_after=checksum(folder/'payload')
        if actual != digest or size_after != size:
            raise RetentionError('STAGED_BYTES_MISMATCH')
        manifest['phase']='staged'
        atomic_json(folder/'manifest.json',manifest)
        append_audit(root,{'event':'staged','entry_id':entry_id,'name':name,'sha256':digest,'size_bytes':size})
        staged.append({'entry_id':entry_id,'name':name,'sha256':digest,'size_bytes':size})
    return {'status':'ok','operation':'stage','dry_run':False,'staged_count':len(staged),
            'items':staged,'purge_available':False,'physical_deletion_count':0}


def stage(root: Path, days: int, at: str | None, apply: bool) -> dict[str, Any]:
    if not apply:
        return _stage_unlocked(root, days, at, False)
    initial = _stage_unlocked(root, days, at, False)
    if initial['counts']['hold'] or not initial['counts']['candidate']:
        return initial
    with demo_lock(root):
        return _stage_unlocked(root, days, at, True)


def _restore_unlocked(root:Path, entry_id:str, apply:bool) ->dict[str,Any]:
    marker=demo_marker(root)
    preflight_trash(root)
    if not ENTRY_ID.fullmatch(entry_id):
        raise RetentionError('BAD_ENTRY_ID')
    folder=root/TRASH/entry_id
    manifest=read_json(folder/'manifest.json',MAX_MANIFEST_BYTES)
    if manifest['sandbox_id']!=marker['sandbox_id'] or manifest['phase']!='staged':
        raise RetentionError('ENTRY_NOT_RESTORABLE')
    name=manifest['name']
    original=root/name
    if original.exists() or original.is_symlink():
        raise RetentionError('RESTORE_TARGET_EXISTS')
    digest,size=checksum(folder/'payload')
    if digest!=manifest['sha256'] or size!=manifest['size_bytes']:
        raise RetentionError('RESTORE_PAYLOAD_MISMATCH')
    if not apply:
        return {'status':'ok','operation':'restore','dry_run':True,'entry_id':entry_id,
                'name':name,'restored_count':0,'reason':'APPLY_REQUIRED'}
    if os.name!='posix':
        raise RetentionError('RESTORE_POSIX_DEMO_ONLY')
    os.replace(folder/'payload',original)
    sync_dir(root)
    manifest['phase']='restored'
    atomic_json(folder/'manifest.json',manifest)
    append_audit(root,{'event':'restored','entry_id':entry_id,'name':name,'sha256':digest,'size_bytes':size})
    return {'status':'ok','operation':'restore','dry_run':False,'entry_id':entry_id,
            'name':name,'restored_count':1,'sha256':digest,'purge_available':False}


def restore(root: Path, entry_id: str, apply: bool) -> dict[str, Any]:
    if apply:
        with demo_lock(root):
            return _restore_unlocked(root, entry_id, True)
    return _restore_unlocked(root, entry_id, False)


def demo_init(root:Path) ->dict[str,Any]:
    root=real_dir(root)
    temp_root=real_dir(Path(tempfile.gettempdir()))
    if root==temp_root or temp_root not in root.parents:
        raise RetentionError('DEMO_ROOT_MUST_BE_INSIDE_OS_TEMP')
    if any(root.iterdir()):
        raise RetentionError('DEMO_ROOT_MUST_BE_EMPTY')
    marker={'schema_version':1,'synthetic':True,'sandbox_id':uuid.uuid4().hex}
    atomic_json(root/MARKER,marker)
    now_ns,_=as_of_ns(None)
    demos=[('old-disposable.txt','disposable',15),('fresh-disposable.txt','disposable',13),
           ('permanent.txt','permanent',60)]
    for name,tag,age in demos:
        path=root/name
        with path.open('x',encoding='utf-8') as stream:
            stream.write('This is invented demonstration content, not user data.\n')
        target=int(now_ns)-age*DAY_NS
        os.utime(path,ns=(target,target))
    (root/'unregistered.txt').write_text('Unregistered synthetic fixture.\n',encoding='utf-8')
    atomic_json(root/RECORD,{'version':1,'entries':[{'path':n,'class':tag} for n,tag,_ in demos]})
    return {'status':'ok','operation':'demo-init','synthetic':True,'created_example_files':4,
            'registered_entries':3,'physical_deletion_count':0,'purge_available':False}


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description='Retention Manager: synthetic sandbox staging ONLY; no purge')
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--age-days',type=int,default=14)
    parser.add_argument('--as-of',help='Optional offset-aware ISO-8601 synthetic test time')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('demo-init')
    sub.add_parser('preview')
    mover=sub.add_parser('stage')
    mover.add_argument('--apply',action='store_true')
    rest=sub.add_parser('restore')
    rest.add_argument('--entry-id',required=True)
    rest.add_argument('--apply',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=real_dir(args.root)
        if args.command=='demo-init':
            output=demo_init(root)
        elif args.command=='preview':
            output=report(root,args.age_days,args.as_of)
        elif args.command=='stage':
            output=stage(root,args.age_days,args.as_of,args.apply)
        else:
            output=restore(root,args.entry_id,args.apply)
        print(json.dumps(output,sort_keys=True,ensure_ascii=False))
        return 2 if output['status']=='partial' else 0
    except (RetentionError,OSError,ValueError,TypeError) as exc:
        code=exc.code if isinstance(exc,RetentionError) else 'UNEXPECTED_IO_FAILURE'
        print(json.dumps({'status':'error','code':code,'operation':args.command,
                          'physical_deletion_count':0,'purge_available':False}))
        return 1

if __name__=='__main__':
    sys.exit(main())
