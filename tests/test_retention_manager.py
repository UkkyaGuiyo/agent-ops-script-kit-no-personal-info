# Copyright (C) 2026 Contributors to Agent Ops Script Kit
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic-only tests for demo-scoped retention staging (GPL-3.0-only)."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'scripts'/'retention_manager.py'
spec=importlib.util.spec_from_file_location('retention_manager_under_test',SOURCE)
rm=importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(rm)

class RetentionCase(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name)/'demo'
        self.root.mkdir()
        self.demo=rm.demo_init(self.root)
    def preview(self, days=14,at=None):
        return rm.report(self.root,days,at)
    def run_cli(self,*args):
        p=subprocess.run([sys.executable,str(SOURCE),'--root',str(self.root),*args],capture_output=True,text=True)
        self.assertTrue(p.stdout,p.stderr)
        return p.returncode,json.loads(p.stdout)
    def set_records(self, entries):
        rm.atomic_json(self.root/rm.RECORD,{'version':1,'entries':entries})
    def sha(self,path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def snapshots(self):
        return {p.name:(self.sha(p),p.stat().st_mtime_ns) for p in self.root.iterdir() if p.is_file()}
    def stage(self):
        return rm.stage(self.root,14,None,True)

class TestPreview(RetentionCase):
    def test_demo_init(self):
        self.assertEqual(self.demo['created_example_files'],4)
    def test_three_registered(self):
        self.assertEqual(len(rm.records(self.root)),3)
    def test_shared_organizer_schema_integration(self):
        organizer = Path(__file__).resolve().parents[1] / 'scripts' / 'organizer.py'
        if not organizer.is_file():
            self.skipTest('full public clone required for Organizer integration')
        module_spec = importlib.util.spec_from_file_location('organizer_from_full_repo', organizer)
        module = importlib.util.module_from_spec(module_spec)
        assert module_spec.loader
        module_spec.loader.exec_module(module)
        config_path = self.root / 'organizer-synthetic-config.json'
        config_path.write_text(json.dumps({'version':1,'age_days':14,'roots':[
            {'name':'synthetic-root','path':str(self.root),'exclude_subtrees':[]}]}))
        config=module.load_config(config_path)
        result=module.propose(config)
        self.assertEqual(result['counts']['candidate'], self.preview()['counts']['candidate'])
        self.assertEqual(result['counts']['not_due'], self.preview()['counts']['not_due'])
        self.assertEqual(result['counts']['excluded'], self.preview()['counts']['excluded'])

    def test_old_disposable_candidate(self):
        self.assertEqual(self.preview()['counts']['candidate'],1)
    def test_fresh_not_due(self):
        self.assertEqual(self.preview()['counts']['not_due'],1)
    def test_permanent_excluded(self):
        self.assertEqual(self.preview()['counts']['excluded'],1)
    def test_unregistered_not_scanned(self):
        self.assertFalse(self.preview()['unregistered_files_scanned'])
    def test_unregistered_not_in_items(self):
        self.assertNotIn('unregistered.txt',[x['name'] for x in self.preview()['items']])
    def test_read_only_sha_mtime(self):
        before=self.snapshots();self.preview();self.assertEqual(before,self.snapshots())
    def test_no_trash_created_by_preview(self):
        self.preview();self.assertFalse((self.root/'.trash').exists())
    def test_threshold_equal(self):
        f=self.root/'old-disposable.txt';now=f.stat().st_mtime_ns+14*rm.DAY_NS
        stamp=rm.dt.datetime.fromtimestamp(now/1e9,rm.dt.timezone.utc).isoformat()
        self.assertEqual(rm.evaluate(self.root,rm.records(self.root),now,14)[0]['decision'],'candidate')
    def test_threshold_below_one_ns(self):
        f=self.root/'old-disposable.txt';now=f.stat().st_mtime_ns+14*rm.DAY_NS-1
        self.assertEqual(rm.evaluate(self.root,rm.records(self.root),now,14)[0]['decision'],'not_due')
    def test_threshold_plus_ns(self):
        f=self.root/'old-disposable.txt';now=f.stat().st_mtime_ns+14*rm.DAY_NS+1
        self.assertEqual(rm.evaluate(self.root,rm.records(self.root),now,14)[0]['decision'],'candidate')
    def test_configurable_threshold(self):
        self.assertEqual(self.preview(days=16)['counts']['candidate'],0)
    def test_zero_threshold(self):
        self.assertEqual(self.preview(days=0)['counts']['candidate'],2)
    def test_negative_threshold(self):
        with self.assertRaises(rm.RetentionError):self.preview(days=-1)
    def test_boolean_threshold(self):
        with self.assertRaises(rm.RetentionError):self.preview(days=True)
    def test_large_threshold(self):
        with self.assertRaises(rm.RetentionError):self.preview(days=365001)
    def test_naive_time_fails(self):
        with self.assertRaises(rm.RetentionError):self.preview(at='2026-11-17T00:00:00')
    def test_bad_time_fails(self):
        with self.assertRaises(rm.RetentionError):self.preview(at='nonsense')
    def test_future_mtime_hold(self):
        f=self.root/'old-disposable.txt';future=rm.dt.datetime.now(rm.dt.timezone.utc).timestamp()+1000
        os.utime(f,(future,future))
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_unknown_tag_hold(self):
        self.set_records([{'path':'old-disposable.txt','class':'other'}])
        self.assertEqual(self.preview()['items'][0]['reason'],'UNKNOWN_TAG')
    def test_missing_registered_hold(self):
        self.set_records([{'path':'missing.txt','class':'disposable'}])
        self.assertEqual(self.preview()['items'][0]['reason'],'MISSING_REGISTERED_FILE')
    def test_unsafe_parent_hold(self):
        self.set_records([{'path':'../bad.txt','class':'disposable'}])
        self.assertEqual(self.preview()['items'][0]['reason'],'UNSAFE_OR_UNSUPPORTED_PATH')
    def test_absolute_path_hold(self):
        self.set_records([{'path':'/test.txt','class':'disposable'}])
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_nested_path_hold_for_demo(self):
        self.set_records([{'path':'a/b.txt','class':'disposable'}])
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_folder_not_candidate(self):
        (self.root/'folder.txt').mkdir()
        self.set_records([{'path':'folder.txt','class':'disposable'}])
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_symlink_not_candidate(self):
        (self.root/'linked.txt').symlink_to(self.root/'old-disposable.txt')
        self.set_records([{'path':'linked.txt','class':'disposable'}])
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_hardlink_not_candidate(self):
        os.link(self.root/'old-disposable.txt',self.root/'duplicate.txt')
        self.assertEqual(self.preview()['counts']['hold'],1)
    def test_record_duplicate_path_fail(self):
        self.set_records([{'path':'old-disposable.txt','class':'disposable'}]*2)
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_bad_record_schema(self):
        rm.atomic_json(self.root/rm.RECORD,{'entries':[],'unknown':42})
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_duplicate_json_keys(self):
        (self.root/rm.RECORD).write_text('{"entries":[],"entries":[]}',encoding='utf-8')
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_missing_record_file(self):
        (self.root/rm.RECORD).unlink()
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_record_symlink(self):
        (self.root/rm.RECORD).unlink()
        (self.root/rm.RECORD).symlink_to(self.root/'old-disposable.txt')
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_bad_json(self):
        (self.root/rm.RECORD).write_text('{')
        with self.assertRaises(rm.RetentionError):self.preview()
    def test_unknown_records_hold_blocks_stage(self):
        self.set_records([{'path':'old-disposable.txt','class':'disposable'},{'path':'missing.txt','class':'disposable'}])
        before=self.snapshots();result=self.stage()
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['staged_count'],0)
        self.assertEqual(before,self.snapshots())
    def test_stage_no_apply_unchanged(self):
        before=self.snapshots();r=rm.stage(self.root,14,None,False)
        self.assertEqual(r['staged_count'],0);self.assertEqual(before,self.snapshots())
    def test_cli_preview(self):
        code,x=self.run_cli('preview')
        self.assertEqual((code,x['counts']['candidate'],x['records_changed']),(0,1,0))
    def test_cli_reject_purge(self):
        p=subprocess.run([sys.executable,str(SOURCE),'--root',str(self.root),'purge','--apply'],capture_output=True)
        self.assertNotEqual(p.returncode,0)
    def test_demo_marker_missing_for_stage(self):
        (self.root/rm.MARKER).unlink()
        with self.assertRaises(rm.RetentionError):self.stage()

class TestStageRestore(RetentionCase):
    def test_lock_symlink_blocks_stage(self):
        (self.root/rm.LOCK).symlink_to(self.root/rm.RECORD)
        with self.assertRaises(rm.RetentionError):self.stage()
    def test_lock_is_created_on_apply(self):
        self.stage();self.assertTrue((self.root/rm.LOCK).is_file())
    def test_lock_not_created_on_preview(self):
        self.preview();self.assertFalse((self.root/rm.LOCK).exists())
    def test_lock_busy_blocks_stage(self):
        if os.name != 'posix':self.skipTest('posix only')
        import fcntl
        fd=os.open(self.root/rm.LOCK,os.O_RDWR|os.O_CREAT,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(rm.RetentionError) as cm:self.stage()
            self.assertEqual(cm.exception.code,'DEMO_LOCK_BUSY')
        finally:
            fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
    def test_manifest_missing_fails_closed(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        (self.root/'.trash'/ident/'manifest.json').unlink()
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_manifest_modified_fails_closed(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        manifest_file=self.root/'.trash'/ident/'manifest.json'
        m=rm.read_json(manifest_file,30000)
        m['size_bytes']='invalid'
        rm.atomic_json(manifest_file,m)
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_staged_payload_absent_blocks_next_run(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        (self.root/'.trash'/ident/'payload').rename(self.root/'moved-unexpectedly.txt')
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_original_mtime_preserved_after_restore(self):
        before=(self.root/'old-disposable.txt').stat().st_mtime_ns
        r=self.stage();rm.restore(self.root,r['items'][0]['entry_id'],True)
        self.assertEqual((self.root/'old-disposable.txt').stat().st_mtime_ns,before)
    def test_record_bytes_preserved_stage_restore(self):
        before=self.sha(self.root/rm.RECORD)
        r=self.stage();rm.restore(self.root,r['items'][0]['entry_id'],True)
        self.assertEqual(self.sha(self.root/rm.RECORD),before)
    def test_invalid_entry_id_prevented(self):
        self.stage()
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,'../../escape',True)
    def test_stage_output_not_physical_delete(self):
        result=self.stage()
        self.assertEqual(result['physical_deletion_count'],0)
    def test_trash_already_unrecognized_blocks(self):
        (self.root/'.trash').mkdir()
        (self.root/'.trash'/'unknown.txt').write_text('bad')
        with self.assertRaises(rm.RetentionError):self.stage()
    def test_no_real_file_deleted_by_demo(self):
        digest=self.sha(self.root/'unregistered.txt')
        self.stage()
        self.assertEqual(digest,self.sha(self.root/'unregistered.txt'))
    def test_restore_does_not_delete_manifest(self):
        result=self.stage();ident=result['items'][0]['entry_id']
        rm.restore(self.root,ident,True)
        self.assertTrue((self.root/'.trash'/ident/'manifest.json').exists())

    def test_stage_one_file(self):
        r=self.stage();self.assertEqual(r['staged_count'],1)
    def test_stage_removes_source_only(self):
        self.stage();self.assertFalse((self.root/'old-disposable.txt').exists())
    def test_stage_leaves_permanent(self):
        self.stage();self.assertTrue((self.root/'permanent.txt').exists())
    def test_stage_leaves_fresh(self):
        self.stage();self.assertTrue((self.root/'fresh-disposable.txt').exists())
    def test_stage_leaves_unregistered(self):
        self.stage();self.assertTrue((self.root/'unregistered.txt').exists())
    def test_stage_purge_never_available(self):
        self.assertFalse(self.stage()['purge_available'])
    def test_stage_payload_digest_preserved(self):
        expected=self.sha(self.root/'old-disposable.txt')
        r=self.stage();ident=r['items'][0]['entry_id']
        self.assertEqual(expected,self.sha(self.root/'.trash'/ident/'payload'))
    def test_manifest_contains_original(self):
        r=self.stage();m=rm.read_json(self.root/'.trash'/r['items'][0]['entry_id']/'manifest.json',30000)
        self.assertEqual(m['name'],'old-disposable.txt')
    def test_manifest_phase_staged(self):
        r=self.stage();m=rm.read_json(self.root/'.trash'/r['items'][0]['entry_id']/'manifest.json',30000)
        self.assertEqual(m['phase'],'staged')
    def test_audit_written(self):
        self.stage();self.assertIn('staged',(self.root/'.trash'/'events.jsonl').read_text())
    def test_restore_dry_run(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        self.assertEqual(rm.restore(self.root,ident,False)['restored_count'],0)
    def test_restore_success(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        self.assertEqual(rm.restore(self.root,ident,True)['restored_count'],1)
    def test_restore_exact_bytes(self):
        before=self.sha(self.root/'old-disposable.txt');r=self.stage()
        rm.restore(self.root,r['items'][0]['entry_id'],True)
        self.assertEqual(before,self.sha(self.root/'old-disposable.txt'))
    def test_restore_marks_manifest(self):
        r=self.stage();ident=r['items'][0]['entry_id'];rm.restore(self.root,ident,True)
        self.assertEqual(rm.read_json(self.root/'.trash'/ident/'manifest.json',30000)['phase'],'restored')
    def test_restore_keeps_audit(self):
        r=self.stage();rm.restore(self.root,r['items'][0]['entry_id'],True)
        a=(self.root/'.trash'/'events.jsonl').read_text()
        self.assertEqual([json.loads(x)['event'] for x in a.strip().splitlines()],['staged','restored'])
    def test_no_restore_overwrite(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        (self.root/'old-disposable.txt').write_text('occupant')
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_repeated_restore_not_allowed(self):
        r=self.stage();ident=r['items'][0]['entry_id'];rm.restore(self.root,ident,True)
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_corrupt_payload_block_restore(self):
        r=self.stage();ident=r['items'][0]['entry_id']
        (self.root/'.trash'/ident/'payload').write_text('tampered')
        with self.assertRaises(rm.RetentionError):rm.restore(self.root,ident,True)
    def test_prepared_manifest_blocks_other_apply(self):
        trash=self.root/'.trash';trash.mkdir(exist_ok=True)
        sub=trash/('a'*32);sub.mkdir();rm.atomic_json(sub/'manifest.json',{'phase':'prepared'})
        with self.assertRaises(rm.RetentionError):self.stage()
    def test_trash_symlink_blocked(self):
        (self.root/'.trash').symlink_to(self.root)
        with self.assertRaises(rm.RetentionError):self.stage()
    def test_no_registered_files_after_stage_auto_deleted(self):
        self.stage();self.assertTrue((self.root/rm.RECORD).exists())
    def test_cli_stage_restore(self):
        code,run=self.run_cli('stage','--apply');self.assertEqual(code,0)
        code,done=self.run_cli('restore','--entry-id',run['items'][0]['entry_id'],'--apply')
        self.assertEqual((code,done['restored_count']),(0,1))
    def test_demo_init_only_empty(self):
        with self.assertRaises(rm.RetentionError):rm.demo_init(self.root)
    def test_demo_init_rejects_non_temp(self):
        with self.assertRaises(rm.RetentionError):rm.demo_init(Path('/var'))
    def test_no_purge_function(self):
        self.assertFalse(hasattr(rm,'purge'))

if __name__=='__main__':
    unittest.main()
