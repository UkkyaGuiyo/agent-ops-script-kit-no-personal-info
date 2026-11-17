"""Synthetic only. Tests use disposable temporary roots and state."""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'scripts'))
import untagged_watch as w  # noqa: E402


class UntaggedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / 'root'
        self.root.mkdir()
        self.state_dir = base / 'state'
        self.state_dir.mkdir()
        self.config = base / 'config.json'
        self.config.write_text(json.dumps({'version': 1, 'roots': [{'name': 'sample', 'path': str(self.root)}]}))
        self.records([])
        self.state_path = self.state_dir / w.STATE_NAME

    def records(self, entries):
        (self.root / w.RECORD_NAME).write_text(json.dumps({'entries': entries}), encoding='utf-8')

    def cfg(self):
        return w.load_config(self.config, self.state_dir)

    def do_scan(self):
        return w.scan(self.cfg(), self.state_path)

    def make(self, name):
        file = self.root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('synthetic', encoding='utf-8')
        return file

    def test_initial_baseline_silent(self):
        self.make('old.txt')
        result = self.do_scan()
        self.assertEqual((result['status'], result['new_untagged']), ('baseline', 0))
        self.assertEqual(self.do_scan()['status'], 'ok')

    def test_new_untagged_pending_and_ack(self):
        self.do_scan()
        self.make('new.txt')
        pending = self.do_scan()
        self.assertEqual((pending['status'], pending['report']['count']), ('pending', 1))
        self.assertEqual(pending['report']['items'], [{'root': 'sample', 'relative_path': 'new.txt'}])
        self.assertEqual(self.do_scan()['report']['event_id'], pending['report']['event_id'])
        acked = w.ack(self.cfg(), self.state_path, pending['report']['event_id'])
        self.assertEqual(acked['status'], 'acknowledged')
        self.assertEqual(self.do_scan()['status'], 'ok')

    def test_restart_replays_same_pending_without_new_id(self):
        self.do_scan()
        self.make('notice.txt')
        pending = self.do_scan()
        self.assertEqual(w.scan(self.cfg(), self.state_path), pending)

    def test_ack_without_pending_is_error(self):
        self.do_scan()
        with self.assertRaises(w.WatchFailure):
            w.ack(self.cfg(), self.state_path, 'a' * 32)

    def test_wrong_ack_does_not_advance(self):
        self.do_scan()
        self.make('a.txt')
        pending = self.do_scan()
        with self.assertRaises(w.WatchFailure):
            w.ack(self.cfg(), self.state_path, '0' * 32)
        self.assertEqual(self.do_scan()['report']['event_id'], pending['report']['event_id'])

    def test_new_file_during_pending_is_not_lost(self):
        self.do_scan()
        self.make('a.txt')
        pending = self.do_scan()
        self.make('b.txt')
        w.ack(self.cfg(), self.state_path, pending['report']['event_id'])
        later = self.do_scan()
        self.assertEqual([v['relative_path'] for v in later['report']['items']], ['b.txt'])

    def test_previously_seen_not_realerted_if_later_untagged(self):
        self.make('existing.txt')
        self.do_scan()
        self.assertEqual(self.do_scan()['status'], 'ok')
        self.make('fresh.txt')
        result = self.do_scan()
        self.assertEqual([i['relative_path'] for i in result['report']['items']], ['fresh.txt'])

    def test_disposable_and_permanent_are_both_tagged(self):
        self.records([{'path': 'a.txt', 'class': 'disposable'}, {'path': 'b.txt', 'class': 'permanent'}])
        self.do_scan()
        self.make('a.txt')
        self.make('b.txt')
        self.assertEqual(self.do_scan()['status'], 'ok')

    def test_unknown_nonblank_class_is_hold_not_untagged(self):
        self.records([{'path': 'a.txt', 'class': 'future-value'}])
        self.do_scan()
        self.make('a.txt')
        self.assertEqual(self.do_scan()['status'], 'ok')

    def test_malformed_record_and_missing_record_fail(self):
        (self.root / w.RECORD_NAME).write_text('invalid json', encoding='utf-8')
        with self.assertRaises(w.WatchFailure):
            self.do_scan()
        self.assertFalse(self.state_path.exists())
        (self.root / w.RECORD_NAME).unlink()
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_duplicate_and_unsafe_records_fail(self):
        for entries in (
            [{'path': '../secret', 'class': 'permanent'}],
            [{'path': '/absolute', 'class': 'disposable'}],
            [{'path': 'same', 'class': 'permanent'}, {'path': 'same', 'class': 'disposable'}],
            [{'path': 'file', 'class': ''}],
        ):
            with self.subTest(entries=entries):
                self.records(entries)
                with self.assertRaises(w.WatchFailure):
                    self.do_scan()

    def test_snapshot_digest_mismatch_fails_closed(self):
        self.do_scan()
        raw = json.loads(self.state_path.read_text(encoding='utf-8'))
        raw['payload']['seen'].append(['sample', 'injected.txt'])
        self.state_path.write_text(json.dumps(raw), encoding='utf-8')
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_incomplete_or_unknown_schema_fails_closed(self):
        self.do_scan()
        original = json.loads(self.state_path.read_text(encoding='utf-8'))
        for key, value in [('baseline_complete', False), ('version', 999)]:
            with self.subTest(key=key):
                raw = json.loads(json.dumps(original))
                raw['payload'][key] = value
                raw['sha256'] = w.digest(raw['payload'])
                self.state_path.write_text(json.dumps(raw), encoding='utf-8')
                with self.assertRaises(w.WatchFailure):
                    self.do_scan()

    def test_config_fingerprint_drift_is_error(self):
        self.do_scan()
        cfg = json.loads(self.config.read_text())
        cfg['roots'][0]['exclude_subtrees'] = ['hidden']
        self.config.write_text(json.dumps(cfg))
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_overlapping_roots_are_rejected(self):
        child = self.root / 'sub'
        child.mkdir()
        self.config.write_text(json.dumps({'version': 1, 'roots': [
            {'name': 'one', 'path': str(self.root)},
            {'name': 'two', 'path': str(child)},
        ]}))
        with self.assertRaises(w.WatchFailure):
            self.cfg()

    def test_state_dir_may_not_be_within_root(self):
        inside = self.root / 'state'
        inside.mkdir()
        with self.assertRaises(w.WatchFailure):
            w.load_config(self.config, inside)

    def test_exclusions_and_record_self_ignored(self):
        (self.root / '.git').mkdir()
        (self.root / '.git' / 'hidden.txt').write_text('synthetic')
        (self.root / 'node_modules').mkdir()
        (self.root / 'node_modules' / 'hidden.txt').write_text('synthetic')
        (self.root / 'ignore').mkdir()
        (self.root / 'ignore' / 'hidden.txt').write_text('synthetic')
        cfg = json.loads(self.config.read_text())
        cfg['roots'][0]['exclude_subtrees'] = ['ignore']
        self.config.write_text(json.dumps(cfg))
        self.do_scan()
        self.make('good.txt')
        result = self.do_scan()
        self.assertEqual(result['report']['count'], 1)
        self.assertEqual(result['report']['items'][0]['relative_path'], 'good.txt')

    def test_symlink_not_followed(self):
        outside = self.state_dir / 'not-to-read'
        outside.mkdir()
        (outside / 'private-synthetic.txt').write_text('test')
        try:
            (self.root / 'link').symlink_to(outside, target_is_directory=True)
            (self.root / 'filelink').symlink_to(outside / 'private-synthetic.txt')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        result = self.do_scan()
        self.assertEqual(result['observed_files'], 0)

    def test_partial_scan_error_never_commits(self):
        self.do_scan()
        before = self.state_path.read_bytes()
        with patch('untagged_watch.scan_root', side_effect=w.WatchFailure('Synthetic I/O denial')):
            with self.assertRaises(w.WatchFailure):
                self.do_scan()
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_lock_conflict_exit_3(self):
        (self.state_dir / w.LOCK_NAME).write_text('busy')
        proc = self.cli('scan')
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)['status'], 'locked')

    def test_state_inside_checkout_is_rejected(self):
        # This must fail before trying to read a synthetic user configuration.
        proc = subprocess.run([sys.executable, str(HERE / 'scripts' / 'untagged_watch.py'),
                               'scan', '--config', str(self.config), '--state-dir', str(HERE)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn('outside the public project checkout', proc.stdout)

    def test_cli_unreadable_record_exit_1(self):
        (self.root / w.RECORD_NAME).unlink()
        proc = self.cli('scan')
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)['status'], 'error')
        self.assertNotIn(str(self.root), proc.stdout)

    def test_report_5w1h_and_read_only_root(self):
        self.do_scan()
        sample = self.make('fresh.txt')
        original = sample.read_bytes()
        result = self.do_scan()
        keys = {'when_utc', 'where', 'who', 'what', 'why', 'how', 'count', 'items', 'event_id'}
        self.assertEqual(set(result['report']), keys)
        self.assertEqual(sample.read_bytes(), original)
        self.assertEqual((self.root / w.RECORD_NAME).read_text(), '{"entries": []}')

    def test_invalid_pending_state_after_rehash_fails(self):
        self.do_scan()
        self.make('new.txt')
        self.do_scan()
        raw = json.loads(self.state_path.read_text())
        raw['payload']['pending']['event_id'] = 'wrong'
        raw['sha256'] = w.digest(raw['payload'])
        self.state_path.write_text(json.dumps(raw))
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_no_scan_on_replay_pending(self):
        self.do_scan()
        self.make('new.txt')
        pending = self.do_scan()
        with patch('untagged_watch.scan_root', side_effect=AssertionError('should not rescan')):
            self.assertEqual(self.do_scan()['report']['event_id'], pending['report']['event_id'])

    def test_multiple_roots(self):
        root2 = Path(self.tmp.name) / 'other'
        root2.mkdir()
        (root2 / w.RECORD_NAME).write_text('{"entries": []}')
        cfg = json.loads(self.config.read_text())
        cfg['roots'].append({'name': 'second', 'path': str(root2)})
        self.config.write_text(json.dumps(cfg))
        self.do_scan()
        self.make('one.txt')
        (root2 / 'two.txt').write_text('synthetic')
        self.assertEqual(self.do_scan()['report']['count'], 2)

    def test_cli_baseline_and_pending_and_ack(self):
        self.assertEqual(json.loads(self.cli('scan').stdout)['status'], 'baseline')
        self.make('some.txt')
        p = self.cli('scan')
        self.assertEqual(p.returncode, 0)
        result = json.loads(p.stdout)
        self.assertEqual(result['status'], 'pending')
        ack = self.cli('ack', '--event-id', result['report']['event_id'])
        self.assertEqual(ack.returncode, 0)
        self.assertEqual(json.loads(ack.stdout)['status'], 'acknowledged')
        self.assertEqual(json.loads(self.cli('scan').stdout)['status'], 'ok')

    def cli(self, command, *extra):
        return subprocess.run([sys.executable, str(HERE / 'scripts' / 'untagged_watch.py'), command,
                               '--config', str(self.config), '--state-dir', str(self.state_dir), *extra],
                              capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()

class AdditionalIntegrityTests(unittest.TestCase):
    setUp = UntaggedTests.setUp
    records = UntaggedTests.records
    cfg = UntaggedTests.cfg
    do_scan = UntaggedTests.do_scan
    make = UntaggedTests.make

    def test_unknown_record_schema_version_fail_closed(self):
        (self.root / w.RECORD_NAME).write_text('{"version": 99, "entries": []}')
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_interrupted_initial_state_save_prevents_rebaseline(self):
        (self.state_dir / '.state-temp-interrupted').write_text('interrupted')
        with self.assertRaises(w.WatchFailure):
            self.do_scan()
        self.assertFalse(self.state_path.exists())

    def test_interrupted_pending_state_prevents_ack(self):
        self.do_scan()
        self.make('fresh.txt')
        pending = self.do_scan()
        (self.state_dir / '.state-temp-interrupted').write_text('interrupted')
        with self.assertRaises(w.WatchFailure):
            w.ack(self.cfg(), self.state_path, pending['report']['event_id'])

    def test_state_file_symlink_refused(self):
        outside = self.state_dir / 'other.json'
        outside.write_text('{}')
        try:
            self.state_path.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        with self.assertRaises(w.WatchFailure):
            self.do_scan()

    def test_relative_control_character_refused(self):
        with self.assertRaises(w.WatchFailure):
            w.relative_path('bad\nnewline')

    def test_scan_root_onerror_fail_closed(self):
        with patch('untagged_watch.os.walk') as walk:
            def imitation(root, *, topdown, followlinks, onerror):
                onerror(PermissionError('synthetic permission denial'))
                yield (root, [], [])
            walk.side_effect = imitation
            with self.assertRaises(w.WatchFailure):
                w.scan_root(self.cfg()['roots'][0])


if __name__ == '__main__':
    unittest.main()
