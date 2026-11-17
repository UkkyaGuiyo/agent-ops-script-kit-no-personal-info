# Copyright (C) 2026 Contributors to Agent Ops Script Kit
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic-only tests: never use real conversation, personal paths, or private input."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import injection_size_watch as w  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 17, 0, 0, tzinfo=UTC)


class InjectionSizeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.inputs = self.base / 'inputs'
        self.inputs.mkdir()
        self.state = self.base / 'state'
        self.state.mkdir()
        self.config_file = self.base / 'private-config.json'
        self.file = self.inputs / 'memory.md'
        self.file.write_text('synthetic baseline\n', encoding='utf-8')
        self.configure()

    def configure(self, targets=None, growth=10):
        config = {'version': 1, 'weekly_growth_percent': growth,
                  'targets': targets or [{'name': 'memory', 'path': str(self.file), 'limit_bytes': 60000}]}
        self.config_file.write_text(json.dumps(config), encoding='utf-8')

    def config(self):
        return w.load_config(self.config_file, self.state)

    def measure(self, when=NOW):
        return w.measure(self.config(), self.state, when)

    def test_baseline_no_warning(self):
        result = self.measure()
        self.assertEqual((result['status'], result['total_bytes']), ('ok', len(self.file.read_bytes())))
        self.assertIsNone(result['files'][0]['weekly_growth']['percent'])
        self.assertEqual(result['token_count'], 'UNKNOWN')

    def test_bytes_multilingual_exact(self):
        self.file.write_text('日本語🍣\n', encoding='utf-8')
        result = self.measure()
        self.assertEqual(result['files'][0]['bytes'], len('日本語🍣\n'.encode()))
        self.assertEqual(result['files'][0]['characters'], len('日本語🍣\n'))
        self.assertEqual(result['files'][0]['lines'], 1)

    def test_empty_file(self):
        self.file.write_bytes(b'')
        result = self.measure()
        self.assertEqual((result['total_bytes'], result['files'][0]['characters']), (0, 0))

    def test_threshold_below(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': 20}])
        self.assertFalse(self.measure()['warning'])

    def test_threshold_exact_not_exceeded(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': len(self.file.read_bytes())}])
        self.assertFalse(self.measure()['warning'])

    def test_threshold_one_over_produces_private_draft(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': len(self.file.read_bytes()) - 1}])
        original = self.file.read_bytes()
        result = self.measure()
        self.assertEqual(result['status'], 'warning')
        self.assertEqual(self.file.read_bytes(), original)
        package = self.state / ('package-' + result['package_id'])
        self.assertEqual((package / 'backups' / 'memory.md').read_bytes(), original)
        self.assertEqual((package / 'drafts' / 'memory.draft.md').read_bytes(), original)
        self.assertEqual(json.loads((package / 'self_test.json').read_text())['semantic_or_key_point_review'], 'NOT_ASSESSABLE')

    def test_multiple_targets_sum(self):
        other = self.inputs / 'persona.txt'
        other.write_text('synthetic persona\n')
        self.configure(targets=[{'name': 'memory', 'path': str(self.file)}, {'name': 'persona', 'path': str(other)}])
        result = self.measure()
        self.assertEqual(result['total_bytes'], self.file.stat().st_size + other.stat().st_size)
        self.assertEqual(sum(row['bytes'] for row in result['files']), result['total_bytes'])

    def test_utf8_decode_error_is_not_zero(self):
        self.file.write_bytes(b'\xff\xfe')
        result = self.measure()
        self.assertEqual((result['status'], result['total_bytes']), ('error', None))
        self.assertIsNone(result['warning'])
        self.assertFalse((self.state / w.HISTORY_NAME).exists())

    def test_missing_source_is_not_zero(self):
        self.file.unlink()
        result = self.measure()
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['files'][0]['bytes'], None)

    def test_partial_failure_blocks_total_and_history(self):
        other = self.inputs / 'missing.txt'
        self.configure(targets=[{'name': 'good', 'path': str(self.file)}, {'name': 'missing', 'path': str(other)}])
        result = self.measure()
        self.assertEqual((result['status'], result['total_bytes'], result['history_advanced']), ('error', None, False))
        self.assertEqual(len(result['files']), 2)

    def test_permission_error_mocked(self):
        with patch.object(w, 'read_source', side_effect=w.MeasurementError('Unable to read complete file')):
            result = self.measure()
        self.assertEqual((result['status'], result['total_bytes']), ('error', None))

    def test_corrupt_json_file_is_error(self):
        invalid = self.inputs / 'instructions.json'
        invalid.write_text('{bad')
        self.configure(targets=[{'name': 'j', 'path': str(invalid)}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_json_duplicate_keys_are_error(self):
        invalid = self.inputs / 'instructions.json'
        invalid.write_text('{"a":1,"a":2}')
        self.configure(targets=[{'name': 'j', 'path': str(invalid)}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_json_nan_is_error(self):
        invalid = self.inputs / 'instructions.json'
        invalid.write_text('{"x": NaN}')
        self.configure(targets=[{'name': 'j', 'path': str(invalid)}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_unsupported_format_is_error(self):
        wrong = self.inputs / 'attachment.bin'
        wrong.write_bytes(b'hello')
        self.configure(targets=[{'name': 'b', 'path': str(wrong)}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_file_over_limit_is_error(self):
        with self.file.open('wb') as stream:
            stream.truncate(w.MAX_SOURCE_BYTES + 1)
        self.assertEqual(self.measure()['status'], 'error')

    def test_file_symlink_rejected(self):
        symlink = self.inputs / 'linked.md'
        try:
            symlink.symlink_to(self.file)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.configure(targets=[{'name': 'linked', 'path': str(symlink)}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_duplicate_alias_invalid(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file)},
                                {'name': 'memory', 'path': str(self.file)}])
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_same_file_two_aliases_invalid(self):
        self.configure(targets=[{'name': 'alpha', 'path': str(self.file)},
                                {'name': 'beta', 'path': str(self.file)}])
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_bad_threshold_bool_invalid(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': True}])
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_unknown_schema_invalid(self):
        self.config_file.write_text('{"version":2,"targets":[],"weekly_growth_percent":10}')
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_weekly_growth_after_full_week(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=7))
        self.file.write_bytes(b'a' * 111)
        result = self.measure(NOW)
        row = result['files'][0]
        self.assertEqual(row['weekly_growth']['status'], 'DERIVED_LINEAR_WEEKLY_RATE')
        self.assertEqual(row['weekly_growth']['percent'], 11.0)
        self.assertEqual(result['status'], 'warning')

    def test_weekly_growth_exact_10_not_exceeded(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=7))
        self.file.write_bytes(b'a' * 110)
        self.assertFalse(self.measure(NOW)['warning'])

    def test_growth_not_reported_for_less_than_week(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=1))
        self.file.write_bytes(b'a' * 150)
        result = self.measure(NOW)
        self.assertEqual(result['files'][0]['weekly_growth']['status'], 'UNKNOWN_LESS_THAN_7_DAYS')
        self.assertFalse(result['warning'])

    def test_zero_previous_nonzero_growth(self):
        self.file.write_bytes(b'')
        self.measure(NOW - dt.timedelta(days=7))
        self.file.write_bytes(b'a')
        result = self.measure(NOW)
        self.assertEqual(result['status'], 'warning')
        self.assertEqual(result['files'][0]['weekly_growth']['status'], 'ZERO_BASELINE_INCREASE')

    def test_json_draft_smaller_semantically_equal(self):
        data = self.inputs / 'synthetic.json'
        data.write_text('{\n  "hello": "world",\n  "count": 2\n}\n')
        self.configure(targets=[{'name': 'json', 'path': str(data), 'limit_bytes': 1}])
        original = data.read_bytes()
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        draft = (package / 'drafts' / 'json.draft.json').read_bytes()
        self.assertLess(len(draft), len(original))
        self.assertEqual(w.strict_json(draft.decode()), w.strict_json(original.decode()))
        self.assertEqual(data.read_bytes(), original)
        comparison = json.loads((package / 'comparison.json').read_text())
        self.assertEqual(comparison['total_saved_bytes'], len(original) - len(draft))
        self.assertEqual(json.loads((package / 'classification.json').read_text())['proposals'][0]['public_class'], 'B')

    def test_backup_hash_and_manifest(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': 0}])
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        manifest = json.loads((package / 'manifest.json').read_text())
        for relative, item in manifest['files'].items():
            contents = (package / relative).read_bytes()
            self.assertEqual(hashlib.sha256(contents).hexdigest(), item['sha256'])
            self.assertEqual(len(contents), item['bytes'])

    def test_history_hash_tamper_fail_closed(self):
        self.measure()
        history = self.state / w.HISTORY_NAME
        obj = json.loads(history.read_text())
        obj['payload']['samples'][0]['sizes']['memory'] = 0
        history.write_text(json.dumps(obj))
        with self.assertRaisesRegex(w.MeasurementError, 'hash mismatch'):
            self.measure(NOW + dt.timedelta(days=7))

    def test_marker_missing_fail_closed(self):
        self.measure()
        (self.state / w.MARKER_NAME).unlink()
        with self.assertRaisesRegex(w.MeasurementError, 'Partial'):
            self.measure(NOW + dt.timedelta(days=7))

    def test_history_missing_fail_closed(self):
        self.measure()
        (self.state / w.HISTORY_NAME).unlink()
        with self.assertRaisesRegex(w.MeasurementError, 'Partial'):
            self.measure(NOW + dt.timedelta(days=7))

    def test_orphaned_temp_rejected(self):
        (self.state / (w.TEMP_PREFIX + 'crashed')).write_text('synthetic')
        with self.assertRaisesRegex(w.MeasurementError, 'Interrupted'):
            self.measure()

    def test_config_fingerprint_change_refused(self):
        self.measure()
        self.configure(growth=11)
        with self.assertRaisesRegex(w.MeasurementError, 'mismatch'):
            self.measure(NOW + dt.timedelta(days=7))

    def test_timestamp_monotonic(self):
        self.measure()
        with self.assertRaisesRegex(w.MeasurementError, 'monotonically'):
            self.measure()

    def test_manual_lock_contention_exit_3(self):
        lock = self.state / w.LOCK_NAME
        lock.write_text('locked')
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'injection_size_watch.py'),
                               '--config', str(self.config_file), '--state-dir', str(self.state)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)['status'], 'locked')

    def test_cli_bad_input_exit_1(self):
        self.file.unlink()
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'injection_size_watch.py'),
                               '--config', str(self.config_file), '--state-dir', str(self.state)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIsNone(json.loads(proc.stdout)['total_bytes'])

    def test_state_dir_in_checkout_rejected(self):
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'injection_size_watch.py'),
                               '--config', str(self.config_file), '--state-dir', str(ROOT)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn('outside public project checkout', proc.stdout)

    def test_input_inside_state_dir_refused(self):
        path = self.state / 'bad.md'
        path.write_text('not valid target')
        self.configure(targets=[{'name': 'bad', 'path': str(path)}])
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_does_not_leak_path_or_source_text_to_stdout(self):
        self.file.write_text('secret-shaped synthetic content that must stay private')
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': 0}])
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'injection_size_watch.py'),
                               '--config', str(self.config_file), '--state-dir', str(self.state)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn(str(self.file), proc.stdout)
        self.assertNotIn('secret-shaped synthetic', proc.stdout)

    def test_only_warn_creates_package(self):
        result = self.measure()
        self.assertIsNone(result['package_id'])
        self.assertFalse(any(x.name.startswith('package-') for x in self.state.iterdir()))

    def test_compact_json_no_claimed_saving(self):
        data = self.inputs / 'already.json'
        data.write_text('{"x":1}')
        self.configure(targets=[{'name': 'json', 'path': str(data), 'limit_bytes': 0}])
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        self.assertEqual(json.loads((package / 'classification.json').read_text())['proposals'][0]['public_class'], 'A')
        self.assertEqual(json.loads((package / 'comparison.json').read_text())['total_saved_bytes'], 0)

    def test_json_unicode_round_trip(self):
        data = self.inputs / 'multilingual.json'
        data.write_text(json.dumps({'日本語': '🍣'}, ensure_ascii=False, indent=4))
        self.configure(targets=[{'name': 'json', 'path': str(data), 'limit_bytes': 0}])
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        self.assertEqual(json.loads((package / 'drafts/json.draft.json').read_text()), {'日本語': '🍣'})

    def test_fourteen_day_normalized_growth(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=14))
        self.file.write_bytes(b'a' * 120)
        result = self.measure(NOW)
        self.assertEqual(result['files'][0]['weekly_growth']['percent'], 10.0)
        self.assertFalse(result['warning'])

    def test_growth_below_week_is_unknown_not_false(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=1))
        self.file.write_bytes(b'a' * 120)
        result = self.measure(NOW)
        self.assertIsNone(result['files'][0]['weekly_growth']['exceeded'])

    def test_corrupt_marker_json_errors(self):
        self.measure()
        (self.state / w.MARKER_NAME).write_text('{broken')
        with self.assertRaises(w.MeasurementError):
            self.measure(NOW + dt.timedelta(days=7))

    def test_config_json_duplicate_keys_errors(self):
        self.config_file.write_text('{"version":1,"version":1,"targets":[],"weekly_growth_percent":10}')
        with self.assertRaises(w.MeasurementError):
            self.config()

    def test_path_under_symlink_parent_rejected(self):
        symlink_dir = self.base / 'shortcut'
        try:
            symlink_dir.symlink_to(self.inputs, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlink unavailable')
        self.configure(targets=[{'name': 'linked', 'path': str(symlink_dir / 'memory.md')}])
        self.assertEqual(self.measure()['status'], 'error')

    def test_source_mutation_between_read_and_packaging_fails(self):
        self.configure(targets=[{'name': 'memory', 'path': str(self.file), 'limit_bytes': 0}])
        original = w.read_source
        calls = {'n': 0}

        def altered(path):
            calls['n'] += 1
            if calls['n'] == 2:
                self.file.write_text('changed after first measurement')
            return original(path)

        with patch.object(w, 'read_source', side_effect=altered):
            with self.assertRaisesRegex(w.MeasurementError, 'Source changed'):
                self.measure()
        self.assertFalse((self.state / w.HISTORY_NAME).exists())
        self.assertTrue(any(x.name.startswith(w.TEMP_PREFIX) for x in self.state.iterdir()))

    def test_history_sample_duplicate_time_fails_closed(self):
        self.measure()
        history = self.state / w.HISTORY_NAME
        envelope = json.loads(history.read_text())
        envelope['payload']['samples'].append(envelope['payload']['samples'][0].copy())
        envelope['sha256'] = w.sha256(w.canonical_json(envelope['payload']))
        history.write_text(json.dumps(envelope))
        with self.assertRaisesRegex(w.MeasurementError, 'time order'):
            self.measure(NOW + dt.timedelta(days=7))

    def test_daily_checks_still_use_week_old_baseline(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=8))
        self.file.write_bytes(b'a' * 105)
        self.measure(NOW - dt.timedelta(days=1))
        self.file.write_bytes(b'a' * 120)
        result = self.measure(NOW)
        self.assertTrue(result['warning'])
        row = result['files'][0]
        self.assertEqual(row['previous_bytes'], 105)
        self.assertGreater(row['weekly_growth']['percent'], 10)

    def test_daily_check_previous_delta_not_week_delta(self):
        self.file.write_bytes(b'a' * 100)
        self.measure(NOW - dt.timedelta(days=8))
        self.file.write_bytes(b'a' * 104)
        self.measure(NOW - dt.timedelta(days=1))
        self.file.write_bytes(b'a' * 105)
        result = self.measure(NOW)
        self.assertEqual(result['files'][0]['previous_bytes'], 104)
        self.assertEqual(result['files'][0]['previous_change_percent'], 0.96153846)
        self.assertFalse(result['warning'])

    def test_json_minification_preserves_numeric_spelling(self):
        data = self.inputs / 'numbers.json'
        original = '{ "minus_zero": -0, "exponent": 1e+00, "escaped": "\\u65e5\\n" }'
        data.write_text(original)
        self.configure(targets=[{'name': 'json', 'path': str(data), 'limit_bytes': 0}])
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        draft = (package / 'drafts/json.draft.json').read_text()
        self.assertEqual(draft, '{"minus_zero":-0,"exponent":1e+00,"escaped":"\\u65e5\\n"}')
        self.assertEqual(w.strict_json(draft), w.strict_json(original))

    def test_json_minification_keeps_whitespace_inside_string(self):
        data = self.inputs / 'string.json'
        data.write_text('{ "phrase" : "two spaces  inside" }')
        self.configure(targets=[{'name': 'json', 'path': str(data), 'limit_bytes': 0}])
        result = self.measure()
        package = self.state / ('package-' + result['package_id'])
        draft = (package / 'drafts/json.draft.json').read_text()
        self.assertEqual(json.loads(draft)['phrase'], 'two spaces  inside')


if __name__ == '__main__':
    unittest.main()
