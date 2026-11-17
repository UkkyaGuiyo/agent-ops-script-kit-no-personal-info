#!/usr/bin/env python3
"""Offline measurement of always-loaded AI context files; safe draft proposals only.

Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only
No source file can be modified, replaced, compressed in place, or auto-applied.
"""
from __future__ import annotations

import argparse
import datetime as datetime
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import uuid
from pathlib import Path
from decimal import Decimal
from typing import Any

DEFAULT_LIMIT_BYTES = 60_000  # decimal kB, not KiB
DEFAULT_GROWTH_PERCENT = 10.0
MIN_GROWTH_INTERVAL_SECONDS = 7 * 24 * 60 * 60
MAX_SOURCE_BYTES = 2_000_000
ACCEPTED_EXTENSIONS = frozenset({'.md', '.txt', '.json'})
SAFE_ALIAS = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,47}$')
HISTORY_NAME = 'injection-measurements.json'
MARKER_NAME = '.injection-initialized.json'
LOCK_NAME = '.injection-size.lock'
TEMP_PREFIX = '.injection-temp-'


class MeasurementError(Exception):
    """An input or local state is invalid; do not treat it as an empty reading."""


class LockBusy(MeasurementError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ValueError('Nonfinite JSON number not supported')


def strict_json(text: str) -> object:
    return json.loads(text, object_pairs_hook=no_duplicate_keys, parse_constant=reject_nonfinite)


def real_path_without_symlinks(path: Path, *, must_be_dir: bool) -> Path:
    full = Path(os.path.abspath(path))
    for piece in reversed((full, *full.parents)):
        try:
            mode = piece.lstat().st_mode
        except OSError as exc:
            raise MeasurementError('Path is absent or inaccessible') from exc
        if stat.S_ISLNK(mode):
            raise MeasurementError('Symbolic links are not permitted')
    mode = full.lstat().st_mode
    if must_be_dir and not stat.S_ISDIR(mode):
        raise MeasurementError('Expected an existing directory')
    if not must_be_dir and not stat.S_ISREG(mode):
        raise MeasurementError('Expected a regular file')
    return full


def read_source(path: Path) -> dict[str, Any]:
    full = real_path_without_symlinks(path, must_be_dir=False)
    if full.suffix.lower() not in ACCEPTED_EXTENSIONS:
        raise MeasurementError('Unsupported file format')
    try:
        before = full.stat()
        if before.st_size > MAX_SOURCE_BYTES:
            raise MeasurementError('File exceeds pilot input safety limit')
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(full, flags)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                raise MeasurementError('File is no longer regular')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                contents = stream.read(MAX_SOURCE_BYTES + 1)
            if len(contents) > MAX_SOURCE_BYTES:
                raise MeasurementError('File exceeds pilot input safety limit')
            after_fd = os.fstat(fd)
        finally:
            os.close(fd)
        after_path = full.stat()
        signature = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
        if signature(before) != signature(opened) or signature(after_fd) != signature(after_path) or signature(before) != signature(after_fd):
            raise MeasurementError('Input changed during measurement')
    except (OSError, OverflowError) as exc:
        raise MeasurementError('Unable to read complete file') from exc
    try:
        text = contents.decode('utf-8', errors='strict')
        parsed = strict_json(text) if full.suffix.lower() == '.json' else None
    except (UnicodeError, ValueError) as exc:
        raise MeasurementError('Invalid UTF-8 or JSON content') from exc
    return {
        'bytes': len(contents), 'characters': len(text), 'lines': len(text.splitlines()),
        'sha256': sha256(contents), 'raw': contents, 'parsed': parsed,
        'extension': full.suffix.lower(),
    }


def load_config(config_path: Path, state_dir: Path) -> dict[str, Any]:
    try:
        config = strict_json(config_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise MeasurementError('Cannot read configuration') from exc
    if not isinstance(config, dict) or set(config) != {'version', 'targets', 'weekly_growth_percent'} or type(config['version']) is not int or config['version'] != 1:
        raise MeasurementError('Configuration schema is invalid')
    targets = config['targets']
    if not isinstance(targets, list) or not targets:
        raise MeasurementError('At least one target is required')
    growth = config['weekly_growth_percent']
    if type(growth) not in (int, float) or not 0 <= growth <= 1000:
        raise MeasurementError('Invalid weekly growth threshold')
    normalized = []
    names: set[str] = set()
    locations: set[str] = set()
    for raw in targets:
        if not isinstance(raw, dict) or not {'name', 'path'} <= set(raw) or not set(raw) <= {'name', 'path', 'limit_bytes'}:
            raise MeasurementError('Invalid target schema')
        name, path_text = raw['name'], raw['path']
        limit = raw.get('limit_bytes', DEFAULT_LIMIT_BYTES)
        if not isinstance(name, str) or not SAFE_ALIAS.fullmatch(name) or name in names:
            raise MeasurementError('Invalid or duplicate target alias')
        if not isinstance(path_text, str) or not path_text or '\x00' in path_text:
            raise MeasurementError('Target file path is invalid')
        if type(limit) is not int or limit < 0:
            raise MeasurementError('Limit must be nonnegative bytes')
        path = Path(path_text)
        if not path.is_absolute():
            path = config_path.parent / path
        path = Path(os.path.abspath(path))
        if str(path) in locations:
            raise MeasurementError('Same target file registered multiple times')
        if state_dir in path.parents:
            raise MeasurementError('Target must not be inside the state directory')
        names.add(name)
        locations.add(str(path))
        normalized.append({'name': name, 'path': path, 'limit_bytes': limit})
    normalized.sort(key=lambda x: x['name'])
    identity = {'version': 1, 'weekly_growth_percent': growth,
                'targets': [{'name': t['name'], 'path': str(t['path']), 'limit_bytes': t['limit_bytes']} for t in normalized]}
    return {'targets': normalized, 'weekly_growth_percent': float(growth),
            'config_fingerprint': sha256(canonical_json(identity))}


def atomic_json(path: Path, value: object) -> None:
    payload = canonical_json(value) + b'\n'
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=TEMP_PREFIX, delete=False) as stream:
            temp_path = Path(stream.name)
            if os.name != 'nt':
                os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
        temp_path = None
        sync_directory(path.parent)
    except OSError as exc:
        raise MeasurementError('Cannot commit measurement history') from exc
    finally:
        # Do not remove a crashed or failed commit's temporary artifact silently.
        pass


def sync_directory(path: Path) -> None:
    if os.name != 'nt':
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def ensure_no_interrupted_work(state_dir: Path) -> None:
    try:
        if any(entry.name.startswith(TEMP_PREFIX) for entry in state_dir.iterdir()):
            raise MeasurementError('Interrupted write or package detected; manual inspection required')
    except OSError as exc:
        raise MeasurementError('Cannot inspect local state directory') from exc


def read_history(state_dir: Path, fingerprint: str) -> list[dict[str, Any]]:
    ensure_no_interrupted_work(state_dir)
    marker = state_dir / MARKER_NAME
    history = state_dir / HISTORY_NAME
    for p in (marker, history):
        try:
            if stat.S_ISLNK(p.lstat().st_mode):
                raise MeasurementError('State symlink prohibited')
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise MeasurementError('Cannot inspect state file') from exc
    if marker.exists() != history.exists():
        raise MeasurementError('Partial measurement state; no automatic reset')
    if not marker.exists():
        return []
    try:
        marker_data = strict_json(marker.read_text(encoding='utf-8'))
        envelope = strict_json(history.read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise MeasurementError('Measurement history is unreadable or corrupt') from exc
    if not isinstance(marker_data, dict) or set(marker_data) != {'version', 'config_fingerprint'} or type(marker_data['version']) is not int or marker_data != {'version': 1, 'config_fingerprint': fingerprint}:
        raise MeasurementError('Marker or configuration mismatch')
    if not isinstance(envelope, dict) or set(envelope) != {'payload', 'sha256'} or not isinstance(envelope['sha256'], str):
        raise MeasurementError('History envelope invalid')
    payload = envelope['payload']
    if sha256(canonical_json(payload)) != envelope['sha256']:
        raise MeasurementError('History integrity hash mismatch')
    if not isinstance(payload, dict) or set(payload) != {'version', 'config_fingerprint', 'samples'} or type(payload['version']) is not int or payload['version'] != 1 or payload['config_fingerprint'] != fingerprint:
        raise MeasurementError('Unsupported history schema or configuration changed')
    samples = payload['samples']
    if not isinstance(samples, list):
        raise MeasurementError('Invalid history samples')
    previous_time = None
    expected_names = None
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != {'at', 'sizes'} or not isinstance(sample['sizes'], dict):
            raise MeasurementError('Malformed history entry')
        at = parse_time(sample['at'])
        if previous_time is not None and at <= previous_time:
            raise MeasurementError('History time order invalid')
        previous_time = at
        if expected_names is None:
            expected_names = set(sample['sizes'])
        if set(sample['sizes']) != expected_names:
            raise MeasurementError('History target keys changed')
        if any(type(value) is not int or value < 0 for value in sample['sizes'].values()):
            raise MeasurementError('History contains invalid file sizes')
    return samples


def parse_time(raw: object) -> datetime.datetime:
    if not isinstance(raw, str):
        raise MeasurementError('Time must be ISO-8601 string')
    try:
        t = datetime.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise MeasurementError('Malformed ISO-8601 time') from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise MeasurementError('Time lacks timezone')
    return t.astimezone(datetime.timezone.utc)


def save_history(state_dir: Path, fingerprint: str, samples: list[dict[str, Any]]) -> None:
    marker_path = state_dir / MARKER_NAME
    if not marker_path.exists():
        # Marker first: a crash before the history file exists stays detectable.
        atomic_json(marker_path, {'version': 1, 'config_fingerprint': fingerprint})
    payload = {'version': 1, 'config_fingerprint': fingerprint, 'samples': samples}
    atomic_json(state_dir / HISTORY_NAME, {'payload': payload, 'sha256': sha256(canonical_json(payload))})


class LocalLock:
    def __init__(self, directory: Path):
        self.path = directory / LOCK_NAME
        self.fd: int | None = None

    def __enter__(self) -> 'LocalLock':
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(self.fd, b'active\n')
        except FileExistsError as exc:
            raise LockBusy('Another invocation may be active; inspect lock manually') from exc
        except OSError as exc:
            raise MeasurementError('Cannot establish local lock') from exc
        return self

    def __exit__(self, *_: object) -> None:
        if self.fd is not None:
            os.close(self.fd)
            try:
                self.path.unlink()
            except OSError:
                pass  # fail closed on the next attempt; no automatic recovery


def weekly_growth(now: datetime.datetime, prev: dict[str, Any] | None, alias: str, current_bytes: int,
                  threshold: float) -> dict[str, Any]:
    if prev is None:
        return {'status': 'UNKNOWN_NO_BASELINE', 'percent': None, 'period_days': None, 'exceeded': None}
    prior = prev['sizes'][alias]
    elapsed = (now - parse_time(prev['at'])).total_seconds()
    if elapsed < MIN_GROWTH_INTERVAL_SECONDS:
        return {'status': 'UNKNOWN_LESS_THAN_7_DAYS', 'percent': None,
                'period_days': round(elapsed / 86400, 4), 'exceeded': None}
    if prior == 0:
        if current_bytes == 0:
            return {'status': 'ZERO_BASELINE_BOTH_ZERO', 'percent': 0.0,
                    'period_days': round(elapsed / 86400, 4), 'exceeded': False}
        return {'status': 'ZERO_BASELINE_INCREASE', 'percent': None,
                'period_days': round(elapsed / 86400, 4), 'exceeded': True}
    # Linear normalization across the actual interval; not measured model tokens.
    pct = (Decimal(current_bytes - prior) * Decimal(100) * Decimal(MIN_GROWTH_INTERVAL_SECONDS)
           / (Decimal(prior) * Decimal(str(elapsed))))
    return {'status': 'DERIVED_LINEAR_WEEKLY_RATE', 'percent': round(float(pct), 8),
            'period_days': round(elapsed / 86400, 4), 'exceeded': pct > Decimal(str(threshold))}


def strip_json_whitespace(text: str) -> str:
    """Remove insignificant JSON whitespace without reserializing scalar tokens."""
    output: list[str] = []
    quoted = False
    escape_next = False
    for char in text:
        if quoted:
            output.append(char)
            if escape_next:
                escape_next = False
            elif char == '\\':
                escape_next = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            output.append(char)
        elif char not in (' ', '\t', '\r', '\n'):
            output.append(char)
    return ''.join(output)


def safe_write_bytes(path: Path, data: bytes) -> None:
    try:
        with path.open('xb') as stream:
            if os.name != 'nt':
                os.fchmod(stream.fileno(), 0o600)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise MeasurementError('Cannot create private draft package') from exc


def build_package(state_dir: Path, targets: list[dict[str, Any]], readings: dict[str, dict[str, Any]],
                  measured_at: str, reason: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    package_id = datetime.datetime.fromisoformat(measured_at).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12]
    try:
        staging = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX, dir=state_dir))
        (staging / 'backups').mkdir(mode=0o700)
        (staging / 'drafts').mkdir(mode=0o700)
    except OSError as exc:
        raise MeasurementError('Cannot create private draft staging directory') from exc
    items = []
    classification = []
    tests = []
    for target in targets:
        alias = target['name']
        record = readings[alias]
        original = record['raw']
        extension = record['extension']
        draft = original
        category = 'F'
        explanation = 'Semantic and editorial review required; no rewrite was attempted'
        if extension == '.json':
            candidate = strip_json_whitespace(original.decode('utf-8')).encode('utf-8')
            if len(candidate) < len(original):
                draft = candidate
                category = 'B'
                explanation = 'JSON whitespace-only formatting candidate; parsed data checked'
            else:
                category = 'A'
                explanation = 'Already compact enough; retain byte-identical draft'
        backup_name = alias + extension
        draft_name = alias + '.draft' + extension
        safe_write_bytes(staging / 'backups' / backup_name, original)
        safe_write_bytes(staging / 'drafts' / draft_name, draft)
        original_sha = record['sha256']
        draft_sha = sha256(draft)
        semantic_check = (strict_json(draft.decode('utf-8')) == record['parsed']) if extension == '.json' else (draft == original)
        if not semantic_check or sha256((staging / 'backups' / backup_name).read_bytes()) != original_sha:
            raise MeasurementError('Draft or backup integrity check failed')
        # Re-read source after writing: do not attest an input that changed mid-package.
        if read_source(target['path'])['sha256'] != original_sha:
            raise MeasurementError('Source changed during draft creation')
        item = {'name': alias, 'original_bytes': len(original), 'draft_bytes': len(draft),
                'saved_bytes': len(original) - len(draft), 'original_sha256': original_sha,
                'draft_sha256': draft_sha, 'backup': 'backups/' + backup_name,
                'draft': 'drafts/' + draft_name, 'class': category}
        items.append(item)
        classification.append({'name': alias, 'public_class': category, 'reason': explanation,
                               'original_A_to_F_internal_meanings': 'UNKNOWN'})
        tests.append({'name': alias, 'mechanical_test': 'PASS',
                      'mechanical_basis': 'parsed_json_equivalence' if extension == '.json' else 'byte_identity',
                      'meaning_or_key_points_reconstruction': 'NOT_ASSESSABLE'})
    total_in = sum(row['original_bytes'] for row in items)
    total_out = sum(row['draft_bytes'] for row in items)
    report = {'measured_at_utc': measured_at, 'source_files_unchanged': True,
              'total_original_bytes': total_in, 'total_draft_bytes': total_out,
              'total_saved_bytes': total_in - total_out,
              'reduction_percent': round(100 * (total_in - total_out) / total_in, 6) if total_in else 0.0,
              'items': items}
    safe_write_bytes(staging / 'comparison.json', canonical_json(report) + b'\n')
    safe_write_bytes(staging / 'classification.json', canonical_json({'public_A_to_F': {
        'A': 'Retain as is', 'B': 'Formatting-only JSON candidate',
        'C': 'Condense (manual review only)', 'D': 'Move to on-demand layer (manual only)',
        'E': 'Remove (manual approval only)', 'F': 'Semantic review required'},
        'proposals': classification}) + b'\n')
    safe_write_bytes(staging / 'self_test.json', canonical_json({'mechanical': tests,
        'semantic_or_key_point_review': 'NOT_ASSESSABLE',
        'automatic_application': False}) + b'\n')
    safe_write_bytes(staging / 'audit.json', canonical_json({'trigger': reason,
        'exact_byte_measurement': True, 'model_token_count': 'UNKNOWN',
        'reduction_is_measured_from_draft': True}) + b'\n')
    manifest = {'version': 1, 'package_id': package_id, 'files': {}}
    for file in sorted(staging.rglob('*')):
        if file.is_file():
            manifest['files'][file.relative_to(staging).as_posix()] = {'bytes': file.stat().st_size,
                                                                        'sha256': sha256(file.read_bytes())}
    safe_write_bytes(staging / 'manifest.json', canonical_json(manifest) + b'\n')
    try:
        sync_directory(staging)
        os.replace(staging, state_dir / ('package-' + package_id))
        sync_directory(state_dir)
    except OSError as exc:
        raise MeasurementError('Cannot finalize private draft package') from exc
    return package_id, report


def measure(config: dict[str, Any], state_dir: Path, now: datetime.datetime | None = None) -> dict[str, Any]:
    measured_at = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(datetime.timezone.utc)
    history = read_history(state_dir, config['config_fingerprint'])
    if history and measured_at <= parse_time(history[-1]['at']):
        raise MeasurementError('Measurement time must advance monotonically')
    targets = config['targets']
    results = []
    readings: dict[str, dict[str, Any]] = {}
    failures = []
    previous = history[-1] if history else None
    # A daily monitor must still see growth over seven days; the newest prior
    # measurement is separately reported, never mistaken for a weekly baseline.
    weekly_baseline = next((sample for sample in reversed(history)
                            if (measured_at - parse_time(sample['at'])).total_seconds()
                            >= MIN_GROWTH_INTERVAL_SECONDS), None)
    for target in targets:
        alias = target['name']
        try:
            reading = read_source(target['path'])
        except MeasurementError as exc:
            failures.append(alias)
            results.append({'name': alias, 'status': 'ERROR', 'bytes': None,
                            'reason': str(exc)})
            continue
        readings[alias] = reading
        growth = weekly_growth(measured_at, weekly_baseline or previous, alias, reading['bytes'], config['weekly_growth_percent'])
        previous_bytes = previous['sizes'][alias] if previous is not None else None
        previous_change = (round(float(Decimal(reading['bytes'] - previous_bytes) * Decimal(100)
                              / Decimal(previous_bytes)), 8)
                           if previous_bytes is not None and previous_bytes > 0 else None)
        threshold_exceeded = reading['bytes'] > target['limit_bytes']
        results.append({'name': alias, 'status': 'MEASURED', 'bytes': reading['bytes'],
                        'characters': reading['characters'], 'lines': reading['lines'],
                        'limit_bytes': target['limit_bytes'], 'size_exceeded': threshold_exceeded,
                        'previous_bytes': previous_bytes, 'previous_change_percent': previous_change,
                        'weekly_growth': growth, 'sha256': reading['sha256']})
    if failures:
        return {'status': 'error', 'timestamp_utc': measured_at.isoformat(), 'files': results,
                'failed_targets': failures, 'total_bytes': None, 'warning': None,
                'history_advanced': False, 'error': 'PARTIAL_MEASUREMENT_FAILED'}
    total_bytes = sum(reading['bytes'] for reading in readings.values())
    warnings = [row['name'] for row in results if row['size_exceeded'] or row['weekly_growth']['exceeded'] is True]
    sample = {'at': measured_at.isoformat(), 'sizes': {name: readings[name]['bytes'] for name in sorted(readings)}}
    package_id = None
    comparison = None
    if warnings:
        package_id, comparison = build_package(state_dir, targets, readings, measured_at.isoformat(),
                                               {'exceeded_aliases': warnings,
                                                'growth_threshold_percent': config['weekly_growth_percent']})
    save_history(state_dir, config['config_fingerprint'], history + [sample])
    return {'status': 'warning' if warnings else 'ok', 'timestamp_utc': measured_at.isoformat(),
            'files': results, 'total_bytes': total_bytes, 'warning': bool(warnings),
            'warning_targets': warnings, 'history_advanced': True,
            'package_id': package_id, 'draft_comparison': {k: comparison[k] for k in (
                'total_original_bytes', 'total_draft_bytes', 'total_saved_bytes', 'reduction_percent')}
                if comparison else None,
            'token_count': 'UNKNOWN'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Measure always-injected context bytes; never apply drafts')
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        state_dir = real_path_without_symlinks(args.state_dir, must_be_dir=True)
        checkout = Path(__file__).resolve().parents[1]
        if state_dir == checkout or checkout in state_dir.parents:
            raise MeasurementError('State directory must be outside public project checkout')
        cfg = load_config(args.config, state_dir)
        with LocalLock(state_dir):
            result = measure(cfg, state_dir)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1 if result['status'] == 'error' else 0
    except LockBusy as exc:
        print(json.dumps({'status': 'locked', 'message': str(exc)}, ensure_ascii=False))
        return 3
    except (MeasurementError, OSError, OverflowError) as exc:
        message = str(exc) if isinstance(exc, MeasurementError) else 'Unexpected filesystem error'
        print(json.dumps({'status': 'error', 'message': message}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
