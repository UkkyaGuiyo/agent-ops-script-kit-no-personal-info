# Copyright (C) 2026 Contributors to Agent Ops Script Kit
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic, read-only-only tests. No private files or external services."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import organizer as o  # noqa: E402

NOW = dt.datetime(2026, 11, 17, 12, 0, tzinfo=dt.timezone.utc)


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'synthetic-root'
        self.root.mkdir()
        self.records = self.root / o.RECORD_NAME
        self.config_path = self.home / 'config.json'
        self.write_records([])
        self.write_config()

    def write_records(self, entries, **additional):
        self.records.write_text(json.dumps({'entries': entries, **additional}), encoding='utf-8')

    def write_config(self, age_days=14, roots=None):
        if roots is None:
            roots = [{'name': 'synthetic', 'path': str(self.root), 'exclude_subtrees': []}]
        self.config_path.write_text(json.dumps({'version': 1, 'age_days': age_days, 'roots': roots}), encoding='utf-8')

    def make(self, path, age_days=None, content=b'synthetic', root=None):
        file = (root or self.root) / path
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_bytes(content)
        if age_days is not None:
            target = o.datetime_ns(NOW) - int(age_days * o.DAY_NS)
            os.utime(file, ns=(target, target))
        return file

    def result(self):
        return o.propose(o.load_config(self.config_path), as_of=NOW)

    def cli(self, *extra):
        return subprocess.run([sys.executable, str(HERE / 'scripts' / 'organizer.py'),
                               '--config', str(self.config_path), '--as-of', NOW.isoformat(), *extra],
                              capture_output=True, text=True)

    def test_empty_record_ok(self):
        result = self.result()
        self.assertEqual((result['status'], result['counts']['candidate']), ('ok', 0))
        self.assertFalse(result['unregistered_files_scanned'])

    def test_unregistered_file_not_examined(self):
        self.make('never-registered.txt', age_days=99)
        result = self.result()
        self.assertEqual(result['items'], [])

    def test_disposable_at_14_days_is_candidate(self):
        self.make('old.txt', age_days=14)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        result = self.result()
        self.assertEqual(result['items'][0]['decision'], 'candidate')
        self.assertEqual(result['items'][0]['age_seconds'], 14 * 86400)

    def test_one_nanosecond_before_is_not_due(self):
        f = self.make('not-yet.txt', age_days=14)
        nanosecond = o.datetime_ns(NOW) - 14 * o.DAY_NS + 1
        os.utime(f, ns=(nanosecond, nanosecond))
        self.write_records([{'path':'not-yet.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'], 'not_due')

    def test_one_nanosecond_after_candidate(self):
        f = self.make('old.txt', age_days=14)
        nanosecond = o.datetime_ns(NOW) - 14 * o.DAY_NS - 1
        os.utime(f, ns=(nanosecond,nanosecond))
        self.write_records([{'path':'old.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'], 'candidate')

    def test_13_days_not_due(self):
        self.make('young.txt', age_days=13)
        self.write_records([{'path':'young.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'], 'not_due')

    def test_permanent_excluded_even_if_old(self):
        self.make('keep.txt', age_days=1000)
        self.write_records([{'path':'keep.txt','class':'permanent'}])
        row=self.result()['items'][0]
        self.assertEqual((row['decision'], row['reason']), ('excluded','PERMANENT_TAG'))

    def test_tag_unknown_held_not_candidate(self):
        self.make('hold.txt', age_days=400)
        self.write_records([{'path':'hold.txt','class':'old-label'}])
        r=self.result()
        self.assertEqual((r['status'],r['items'][0]['reason']), ('partial','UNKNOWN_TAG_CLASS'))

    def test_tag_empty_held(self):
        self.write_records([{'path':'any.txt','class':''}])
        self.assertEqual(self.result()['items'][0]['decision'],'hold')

    def test_missing_tagged_file_held(self):
        self.write_records([{'path':'missing.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'MISSING_REGISTERED_FILE')

    def test_missing_permanent_file_held(self):
        self.write_records([{'path':'absent.txt','class':'permanent'}])
        self.assertEqual(self.result()['items'][0]['reason'],'MISSING_REGISTERED_FILE')

    def test_future_mtime_is_hold(self):
        self.make('future.txt', age_days=-1)
        self.write_records([{'path':'future.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'FUTURE_MODIFICATION_TIME')

    def test_age_zero_always_candidate_for_past(self):
        self.make('new.txt', age_days=0)
        self.write_records([{'path':'new.txt','class':'disposable'}])
        self.write_config(age_days=0)
        self.assertEqual(self.result()['items'][0]['decision'],'candidate')

    def test_nested_path(self):
        self.make('sub/nested.txt', age_days=20)
        self.write_records([{'path':'sub/nested.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['relative_path'],'sub/nested.txt')

    def test_relative_path_traversal_held(self):
        self.write_records([{'path':'../escape.txt','class':'disposable'}])
        row=self.result()['items'][0]
        self.assertEqual((row['decision'],row['reason'],row['relative_path']),('hold','UNSAFE_RECORD_PATH',None))

    def test_absolute_path_held(self):
        self.write_records([{'path':str(self.home / 'private.txt'),'class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'UNSAFE_RECORD_PATH')

    def test_windows_drive_path_held(self):
        self.write_records([{'path':'Q:/private.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'UNSAFE_RECORD_PATH')

    def test_windows_backslash_held(self):
        self.write_records([{'path':'sub\\thing.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'UNSAFE_RECORD_PATH')

    def test_malformed_entry_held(self):
        self.write_records([{'path':'okay.txt','class':'disposable', 'extra': 'x'}])
        self.assertEqual(self.result()['items'][0]['reason'],'MALFORMED_ENTRY')

    def test_duplicate_path_is_fail_closed(self):
        self.write_records([{'path':'a.txt','class':'permanent'},{'path':'a.txt','class':'disposable'}])
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_duplicate_json_key_is_fail_closed(self):
        self.records.write_text('{"entries":[],"entries":[]}', encoding='utf-8')
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_unknown_version_fail_closed(self):
        self.write_records([], version=2)
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_record_symlink_fail_closed(self):
        original=self.home / 'other.json'
        original.write_text('{"entries":[]}', encoding='utf-8')
        self.records.unlink()
        try:
            self.records.symlink_to(original)
        except OSError:
            self.skipTest('symlinks not available')
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_tagged_symlink_held(self):
        outside=self.home / 'outside.txt'
        outside.write_text('do not open',encoding='utf-8')
        target=self.root / 'link.txt'
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest('symlinks not available')
        self.write_records([{'path':'link.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'SYMLINK_PATH')

    def test_tagged_parent_symlink_held(self):
        outside=self.home / 'outside'
        outside.mkdir()
        (outside / 'file.txt').write_text('outside',encoding='utf-8')
        try:
            (self.root / 'linkdir').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks not available')
        self.write_records([{'path':'linkdir/file.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'SYMLINK_PATH')

    def test_builtin_trash_is_excluded(self):
        self.write_records([{'path':'.trash/2026-11-01/old.txt','class':'disposable'}])
        row=self.result()['items'][0]
        self.assertEqual((row['decision'],row['reason']),('excluded','EXCLUDED_BY_SCOPE'))

    def test_other_builtin_excluded(self):
        self.write_records([{'path':'sub/node_modules/x.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'],'excluded')

    def test_explicit_subtree_excluded(self):
        self.write_config(roots=[{'name':'synthetic','path':str(self.root),'exclude_subtrees':['do-not-touch']}])
        self.write_records([{'path':'do-not-touch/file.txt','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'],'excluded')

    def test_record_self_reference_excluded(self):
        self.write_records([{'path':o.RECORD_NAME,'class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['decision'],'excluded')

    def test_not_regular_directory_held(self):
        (self.root / 'folder').mkdir()
        self.write_records([{'path':'folder','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'NOT_REGULAR_FILE')

    def test_file_as_parent_held(self):
        self.make('plain.txt', age_days=20)
        self.write_records([{'path':'plain.txt/deeper','class':'disposable'}])
        self.assertEqual(self.result()['items'][0]['reason'],'NOT_A_DIRECTORY')

    def test_two_roots(self):
        second=self.home / 'second'
        second.mkdir()
        (second / o.RECORD_NAME).write_text('{"entries":[{"path":"stay.txt","class":"permanent"}]}')
        self.make('stay.txt',age_days=100,root=second)
        self.make('old.txt',age_days=15)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        self.write_config(roots=[{'name':'first','path':str(self.root),'exclude_subtrees':[]},
                                 {'name':'second','path':str(second),'exclude_subtrees':[]}])
        r=self.result()
        self.assertEqual(r['counts'],{'candidate':1,'not_due':0,'excluded':1,'hold':0})

    def test_overlapping_roots_fail_closed(self):
        nested=self.root / 'nested'
        nested.mkdir()
        self.write_config(roots=[{'name':'first','path':str(self.root),'exclude_subtrees':[]},
                                 {'name':'second','path':str(nested),'exclude_subtrees':[]}])
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_duplicate_root_name_fail_closed(self):
        second=self.home / 'second'
        second.mkdir()
        self.write_config(roots=[{'name':'same','path':str(self.root),'exclude_subtrees':[]},
                                 {'name':'same','path':str(second),'exclude_subtrees':[]}])
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_root_symlink_rejected(self):
        link=self.home / 'link'
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks not available')
        self.write_config(roots=[{'name':'symlink','path':str(link),'exclude_subtrees':[]}])
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_negative_age_invalid(self):
        self.write_config(age_days=-1)
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_age_bool_invalid(self):
        self.write_config(age_days=True)
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_unsupported_config_version(self):
        self.config_path.write_text('{"version":2,"age_days":14,"roots":[]}')
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_missing_record_fail_closed(self):
        self.records.unlink()
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_inaccessible_file_becomes_hold(self):
        self.write_records([{'path':'no-read.txt','class':'disposable'}])
        with patch.object(o,'file_lstat',side_effect=o.OrganizerError('INACCESSIBLE_REGISTERED_FILE')):
            self.assertEqual(self.result()['items'][0]['reason'],'INACCESSIBLE_REGISTERED_FILE')

    def test_mixed_decisions_is_partial_and_reports_all(self):
        self.make('due.txt',age_days=20)
        self.make('future.txt',age_days=1)
        self.make('always.txt',age_days=30)
        self.write_records([{'path':'due.txt','class':'disposable'},
                            {'path':'future.txt','class':'disposable'},
                            {'path':'always.txt','class':'permanent'},
                            {'path':'missing.txt','class':'disposable'}])
        r=self.result()
        self.assertEqual(r['counts'],{'candidate':1,'not_due':1,'excluded':1,'hold':1})
        self.assertEqual(r['status'],'partial')

    def test_cli_partial_exit1(self):
        self.write_records([{'path':'missing.txt','class':'disposable'}])
        result=self.cli()
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout)['status'],'partial')

    def test_cli_candidate_exit0(self):
        self.make('old.txt',age_days=15)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        result=self.cli()
        self.assertEqual(result.returncode,0)
        parsed=json.loads(result.stdout)
        self.assertEqual(parsed['status'],'candidates')
        self.assertTrue(parsed['dry_run'])
        self.assertEqual(parsed['changed_files'],0)

    def test_cli_error_exit1_does_not_report_zero_candidates(self):
        self.records.unlink()
        result=self.cli()
        self.assertEqual(result.returncode,1)
        payload=json.loads(result.stdout)
        self.assertEqual(payload['status'],'error')
        self.assertNotIn('counts',payload)

    def test_cli_unknown_mutating_option_rejected(self):
        result=self.cli('--apply')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'.trash').exists())

    def test_no_source_files_modified_even_candidate(self):
        original=self.make('old.txt',age_days=20)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        paths=[self.config_path,self.records,original]
        hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        times=[p.stat().st_mtime_ns for p in paths]
        self.result()
        self.assertEqual(hashes,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        self.assertEqual(times,[p.stat().st_mtime_ns for p in paths])
        self.assertFalse((self.root/'.trash').exists())

    def test_no_original_content_read(self):
        self.make('private.txt',age_days=15)
        self.write_records([{'path':'private.txt','class':'disposable'}])
        with patch.object(Path,'read_bytes',side_effect=AssertionError('source bytes accessed')):
            self.assertEqual(self.result()['items'][0]['decision'],'candidate')

    def test_record_entries_empty_is_not_proof_no_unregistered_files(self):
        self.make('untracked.txt',age_days=500)
        self.assertFalse(self.result()['unregistered_files_scanned'])

    def test_repeated_scan_has_same_decisions(self):
        self.make('old.txt',age_days=30)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        self.assertEqual(self.result(),self.result())

    def test_numeric_tag_held(self):
        self.write_records([{'path':'any.txt','class':99}])
        self.assertEqual(self.result()['items'][0]['decision'],'hold')

    def test_malformed_json_record_error(self):
        self.records.write_text('{broken',encoding='utf-8')
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_past_config_age_non_integer(self):
        self.write_config(age_days=14.0)
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_safe_exclusion_invalid_is_rejected(self):
        self.write_config(roots=[{'name':'synthetic','path':str(self.root),'exclude_subtrees':['../outside']}])
        with self.assertRaises(o.OrganizerError):
            self.result()

    def test_invalid_as_of_without_timezone_errors(self):
        with self.assertRaises(o.OrganizerError):
            o.propose(o.load_config(self.config_path),as_of=dt.datetime(2026,11,17,0,0))

    def test_utc_with_timezone_offset(self):
        self.make('old.txt',age_days=14)
        self.write_records([{'path':'old.txt','class':'disposable'}])
        alt=NOW.astimezone(dt.timezone(dt.timedelta(hours=9)))
        self.assertEqual(o.propose(o.load_config(self.config_path),as_of=alt)['items'][0]['decision'],'candidate')


if __name__=='__main__':
    unittest.main()
