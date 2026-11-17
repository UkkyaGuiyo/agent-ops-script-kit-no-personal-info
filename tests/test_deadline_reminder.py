# Copyright (C) 2026 Contributors to Agent Ops Script Kit
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic-only safety and contract tests for the one-shot reminder. GPL-3.0-only."""
import contextlib
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import deadline_reminder as r

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 17, 2, 0, 0, tzinfo=UTC)


def make_due(when=NOW, zone='Asia/Tokyo'):
    return {'utc': when.astimezone(UTC).isoformat(timespec='seconds'),
            'local': when.astimezone(ZoneInfo(zone)).isoformat(timespec='seconds'),
            'timezone': zone, 'epoch_seconds': int((when.astimezone(UTC)-r.EPOCH).total_seconds())}


def make_item(when=NOW, origin='synthetic-source', condition='synthetic-rule', zone='Asia/Tokyo'):
    return {'schema_version': 1, 'origin_id': origin, 'condition_id': condition, 'due': make_due(when, zone)}


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'state'
        self.root.mkdir()
        self.file = Path(self.tmp.name) / 'input.json'

    def register(self, item=None):
        return r.register(self.root, item or make_item())

    def state(self):
        return r.load_journal(self.root)

    def due(self, when=NOW, zone='Asia/Tokyo'):
        return make_due(when, zone)

    def call(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = r.main(['--state-dir', str(self.root), *args])
        return code, json.loads(buf.getvalue())

    def file_json(self, obj):
        self.file.write_text(json.dumps(obj), encoding='utf-8')
        return self.file

    def report(self):
        return r.report(self.root)

    def test_initial_state_empty(self):
        self.assertEqual(self.state()['next_seq'], 1)

    def test_initial_report_has_no_items(self):
        result=self.report()
        self.assertEqual(result['items'], [])
        self.assertEqual(result['pending_count'], 0)

    def test_initial_report_marks_derived_missing(self):
        self.assertIn('outbox:missing', self.report()['derived_warnings'])

    def test_register_deterministic_id(self):
        a=self.register()
        self.assertEqual(a['reminder_id'], r.item_id(make_item()))
        self.assertEqual(a['added'], True)

    def test_register_duplicate_no_event(self):
        self.register()
        result=self.register()
        self.assertFalse(result['added'])
        self.assertEqual(self.state()['next_seq'], 2)

    def test_registration_hash_uses_due(self):
        self.assertNotEqual(r.item_id(make_item()), r.item_id(make_item(NOW+dt.timedelta(seconds=1))))

    def test_registration_hash_uses_origin(self):
        self.assertNotEqual(r.item_id(make_item()),r.item_id(make_item(origin='other')))

    def test_registration_hash_uses_condition(self):
        self.assertNotEqual(r.item_id(make_item()),r.item_id(make_item(condition='other')))

    def test_before_due_no_firing(self):
        self.register()
        result=r.run_check(self.root,NOW-dt.timedelta(seconds=1))
        self.assertEqual(result['new_fired_count'], 0)
        self.assertEqual(result['pending_delivery_count'], 0)

    def test_exact_due_fires(self):
        self.register()
        result=r.run_check(self.root,NOW)
        self.assertEqual(result['new_fired_count'],1)
        self.assertEqual(result['pending_delivery_count'],1)

    def test_after_due_fires(self):
        self.register()
        self.assertEqual(r.run_check(self.root,NOW+dt.timedelta(seconds=1))['new_fired_count'],1)

    def test_check_twice_fires_once(self):
        self.register()
        r.run_check(self.root,NOW)
        result=r.run_check(self.root,NOW+dt.timedelta(minutes=2))
        self.assertEqual(result['new_fired_count'],0)
        self.assertEqual(result['pending_delivery_count'],1)
        self.assertEqual(self.state()['next_seq'],3)

    def test_pending_outbox_id_is_stable(self):
        rid=self.register()['reminder_id']
        r.run_check(self.root,NOW)
        out=self.report()['outbox'][0]
        self.assertEqual(out['outbox_id'],r.outbox_id(rid))
        self.assertEqual(out['delivery_state'],'pending')

    def test_no_external_delivery_attempt(self):
        self.register()
        result=r.run_check(self.root,NOW)
        self.assertEqual(result['delivery_attempts'],0)
        self.assertEqual(result['external_delivery'],'NONE')

    def test_local_reconcile_missing_outbox(self):
        self.register()
        r.run_check(self.root,NOW)
        (self.root/r.OUTBOX).unlink()
        result=r.run_check(self.root,NOW+dt.timedelta(seconds=1))
        self.assertEqual(result['new_fired_count'],0)
        self.assertEqual(self.report()['derived_warnings'],[])

    def test_local_reconcile_stale_outbox(self):
        self.register()
        r.run_check(self.root,NOW)
        (self.root/r.OUTBOX).write_text('{}')
        self.assertIn('outbox:stale',self.report()['derived_warnings'])
        r.run_check(self.root,NOW+dt.timedelta(seconds=1))
        self.assertFalse(self.report()['derived_warnings'])

    def test_repair_outbox_preserves_journal(self):
        self.register()
        r.run_check(self.root,NOW)
        path=self.root/r.JOURNAL
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        (self.root/r.OUTBOX).write_text('corrupt')
        result=r.report(self.root)
        self.assertIn('outbox:unreadable', result['derived_warnings'])
        r.refresh_outbox(self.root,self.state())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_cancel_active(self):
        rid=self.register()['reminder_id']
        self.assertTrue(r.cancel(self.root,rid)['changed'])
        self.assertEqual(self.state()['items'][rid]['status'],'cancelled')

    def test_cancel_duplicate(self):
        rid=self.register()['reminder_id']
        r.cancel(self.root,rid)
        self.assertFalse(r.cancel(self.root,rid)['changed'])

    def test_cancelled_never_fires(self):
        rid=self.register()['reminder_id']
        r.cancel(self.root,rid)
        self.assertEqual(r.run_check(self.root,NOW)['new_fired_count'],0)

    def test_cancel_fired_rejected(self):
        rid=self.register()['reminder_id']
        r.run_check(self.root,NOW)
        with self.assertRaises(r.ReminderError):r.cancel(self.root,rid)

    def test_cancel_missing_rejected(self):
        with self.assertRaises(r.ReminderError):r.cancel(self.root,'rem-notfound')

    def test_reschedule_changes_identity(self):
        old=self.register()['reminder_id']
        result=r.reschedule(self.root,old,self.due(NOW+dt.timedelta(days=1)))
        self.assertNotEqual(result['new_id'],old)
        self.assertEqual(self.state()['items'][old]['status'],'cancelled')
        self.assertEqual(self.state()['items'][result['new_id']]['status'],'active')

    def test_reschedule_duplicate_is_idempotent(self):
        old=self.register()['reminder_id']
        new_due=self.due(NOW+dt.timedelta(days=1))
        a=r.reschedule(self.root,old,new_due)
        b=r.reschedule(self.root,old,new_due)
        self.assertEqual(a['new_id'],b['new_id'])
        self.assertFalse(b['changed'])

    def test_reschedule_same_due_no_event(self):
        old=self.register()['reminder_id']
        self.assertFalse(r.reschedule(self.root,old,self.due())['changed'])
        self.assertEqual(self.state()['next_seq'],2)

    def test_reschedule_fired_rejected(self):
        old=self.register()['reminder_id']
        r.run_check(self.root,NOW)
        with self.assertRaises(r.ReminderError):r.reschedule(self.root,old,self.due(NOW+dt.timedelta(days=1)))

    def test_rescheduled_does_not_fire_old(self):
        old=self.register()['reminder_id']
        r.reschedule(self.root,old,self.due(NOW+dt.timedelta(days=1)))
        self.assertEqual(r.run_check(self.root,NOW)['new_fired_count'],0)
        self.assertEqual(r.run_check(self.root,NOW+dt.timedelta(days=1))['new_fired_count'],1)

    def test_epoch_integer_exact(self):
        self.assertEqual(r.validate_due(self.due())['epoch_seconds'],int((NOW-r.EPOCH).total_seconds()))

    def test_timezone_three_forms_match(self):
        self.assertEqual(r.validate_due(self.due(zone='Asia/Tokyo'))['timezone'],'Asia/Tokyo')

    def test_another_zone_valid(self):
        self.assertEqual(r.validate_due(self.due(zone='America/New_York'))['timezone'],'America/New_York')

    def test_timezone_mismatch_rejected(self):
        obj=self.due();obj['timezone']='Europe/London'
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_local_time_mismatch_rejected(self):
        obj=self.due();obj['local']='2026-11-17T12:00:00+09:00'
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_epoch_mismatch_rejected(self):
        obj=self.due();obj['epoch_seconds']+=1
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_epoch_bool_rejected(self):
        obj=self.due();obj['epoch_seconds']=True
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_epoch_float_rejected(self):
        obj=self.due();obj['epoch_seconds']=float(obj['epoch_seconds'])
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_epoch_string_rejected(self):
        obj=self.due();obj['epoch_seconds']=str(obj['epoch_seconds'])
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_utc_offset_not_zero_rejected(self):
        obj=self.due();obj['utc']=obj['local']
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_utc_ambiguous_Z_rejected(self):
        obj=self.due();obj['utc']=obj['utc'].replace('+00:00','Z')
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_unknown_timezone_rejected(self):
        obj=self.due();obj['timezone']='Synthetic/No_Such_Zone'
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_nonexistent_local_hour_rejected(self):
        when=dt.datetime(2026,3,8,7,30,tzinfo=UTC)
        obj=self.due(when, zone='America/New_York')
        obj['local']='2026-03-08T02:30:00-05:00'
        with self.assertRaises(r.ReminderError):r.validate_due(obj)

    def test_ambiguous_dst_hour_can_roundtrip(self):
        when=dt.datetime(2026,11,1,6,30,tzinfo=UTC)
        self.assertEqual(r.validate_due(self.due(when, zone='America/New_York'))['timezone'],'America/New_York')

    def test_wrong_schema_version_rejected(self):
        raw=make_item();raw['schema_version']=2
        with self.assertRaises(r.ReminderError):r.validate_item(raw)

    def test_missing_field_rejected(self):
        raw=make_item();raw.pop('condition_id')
        with self.assertRaises(r.ReminderError):r.validate_item(raw)

    def test_invalid_id_rejected(self):
        raw=make_item();raw['origin_id']='../../bad'
        with self.assertRaises(r.ReminderError):r.validate_item(raw)

    def test_extra_fields_rejected(self):
        raw=make_item();raw['message']='secret'
        with self.assertRaises(r.ReminderError):r.validate_item(raw)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(r.ReminderError):r.decode(b'{"a":1,"a":2}')

    def test_nan_rejected(self):
        with self.assertRaises(r.ReminderError):r.decode(b'{"x":NaN}')

    def test_journal_broken_json_fails_closed(self):
        self.register()
        before=(self.root/r.JOURNAL).read_bytes()
        (self.root/r.JOURNAL).write_bytes(before+b'broken\n')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        self.assertEqual((self.root/r.JOURNAL).read_bytes(),before+b'broken\n')

    def test_partial_journal_line_fails_closed(self):
        self.register()
        with (self.root/r.JOURNAL).open('ab') as f:f.write(b'{"not_end":true}')
        with self.assertRaises(r.ReminderError):r.load_journal(self.root)

    def test_unknown_journal_version_fails_closed(self):
        self.register()
        path=self.root/r.JOURNAL
        obj=json.loads(path.read_text());obj['version']=3
        path.write_bytes(r.canonical(obj)+b'\n')
        with self.assertRaises(r.ReminderError):r.load_journal(self.root)

    def test_journal_gap_fails_closed(self):
        self.register()
        path=self.root/r.JOURNAL
        obj=json.loads(path.read_text());obj['seq']=2
        path.write_bytes(r.canonical(obj)+b'\n')
        with self.assertRaises(r.ReminderError):r.load_journal(self.root)

    def test_failure_ledger_survives_corrupt_journal(self):
        self.register()
        path=self.root/r.JOURNAL
        before=path.read_bytes();path.write_bytes(before+b'broken\n')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        payload=r.read_json(self.root/r.FAILURES)['payload']
        self.assertEqual(payload['open_code'],'BAD_JOURNAL')
        self.assertEqual(len(payload['occurrences']),1)

    def test_failure_episode_deduplicated(self):
        self.register();path=self.root/r.JOURNAL
        before=path.read_bytes();path.write_bytes(before+b'bad\n')
        for _ in range(3):
            with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        self.assertEqual(len(r.read_json(self.root/r.FAILURES)['payload']['occurrences']),1)

    def test_failure_resolution_then_recurrence_is_new(self):
        self.register();path=self.root/r.JOURNAL
        before=path.read_bytes();path.write_bytes(before+b'bad\n')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        path.write_bytes(before)
        r.run_check(self.root,NOW-dt.timedelta(days=1))
        self.assertIsNone(r.read_json(self.root/r.FAILURES)['payload']['open_code'])
        path.write_bytes(before+b'bad\n')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        self.assertEqual(len(r.read_json(self.root/r.FAILURES)['payload']['occurrences']),2)

    def test_failure_hash_tampering_rejected(self):
        r.write_failure(self.root,'BAD_JOURNAL',NOW)
        path=self.root/r.FAILURES
        obj=json.loads(path.read_text());obj['payload']['open_code']='FAKE'
        path.write_text(json.dumps(obj))
        with self.assertRaises(r.ReminderError):r.write_failure(self.root,'',NOW)

    def test_unknown_cancelled_not_delivered(self):
        rid=self.register()['reminder_id'];r.cancel(self.root,rid)
        self.assertEqual(self.report()['outbox'],[])

    def test_ack_requires_valid_receipt(self):
        self.register();r.run_check(self.root,NOW)
        oid=self.report()['outbox'][0]['outbox_id']
        for raw in [{},{'schema_version':1,'status':'failed','outbox_id':oid,'consumer_id':'sink','receipt_id':'receipt'},
                    {'schema_version':1,'status':'accepted','outbox_id':'out-wrong','consumer_id':'sink','receipt_id':'receipt'}]:
            with self.assertRaises(r.ReminderError):r.acknowledge(self.root,oid,raw)

    def test_ack_delivered_is_manual_attestation_not_sink_check(self):
        self.register();r.run_check(self.root,NOW)
        oid=self.report()['outbox'][0]['outbox_id']
        receipt={'schema_version':1,'status':'accepted','outbox_id':oid,'consumer_id':'offline-test','receipt_id':'receipt-one'}
        result=r.acknowledge(self.root,oid,receipt)
        self.assertTrue(result['changed'])
        self.assertFalse(result['consumer_verified'])
        self.assertEqual(self.report()['pending_count'],0)
        self.assertEqual(self.report()['delivered_attested_count'],1)

    def test_ack_repeated_receipt_idempotent(self):
        self.register();r.run_check(self.root,NOW)
        oid=self.report()['outbox'][0]['outbox_id']
        receipt={'schema_version':1,'status':'accepted','outbox_id':oid,'consumer_id':'offline-test','receipt_id':'receipt-one'}
        r.acknowledge(self.root,oid,receipt)
        seq=self.state()['next_seq']
        self.assertFalse(r.acknowledge(self.root,oid,receipt)['changed'])
        self.assertEqual(self.state()['next_seq'],seq)

    def test_ack_conflict_rejected(self):
        self.register();r.run_check(self.root,NOW)
        oid=self.report()['outbox'][0]['outbox_id']
        receipt={'schema_version':1,'status':'accepted','outbox_id':oid,'consumer_id':'offline-test','receipt_id':'receipt-one'}
        r.acknowledge(self.root,oid,receipt)
        receipt['receipt_id']='another-receipt'
        with self.assertRaises(r.ReminderError):r.acknowledge(self.root,oid,receipt)

    def test_ack_consumer_change_rejected(self):
        self.register();r.run_check(self.root,NOW)
        oid=self.report()['outbox'][0]['outbox_id']
        receipt={'schema_version':1,'status':'accepted','outbox_id':oid,'consumer_id':'offline-test','receipt_id':'receipt-one'}
        r.acknowledge(self.root,oid,receipt)
        receipt['consumer_id']='other-sink'
        with self.assertRaises(r.ReminderError):r.acknowledge(self.root,oid,receipt)

    def test_lock_contention_gives_exit_3(self):
        with r.Lock(self.root):
            code,body=self.call('check')
            self.assertEqual(code,3)
            self.assertEqual(body['code'],'LOCKED')

    def test_temp_orphan_blocks_check(self):
        self.register()
        (self.root/(r.TEMP_PREFIX+'synthetic')).write_text('x')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)

    def test_temp_orphan_does_not_disappear(self):
        self.register()
        path=self.root/(r.TEMP_PREFIX+'synthetic');path.write_text('x')
        with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        self.assertTrue(path.exists())

    def test_symlink_state_dir_rejected(self):
        link=Path(self.tmp.name)/'linked'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(r.ReminderError):r.validate_root(link)

    def test_symlink_journal_rejected(self):
        target=Path(self.tmp.name)/'actual';target.write_text('text')
        (self.root/r.JOURNAL).symlink_to(target)
        with self.assertRaises(r.ReminderError):r.load_journal(self.root)

    def test_state_dir_missing_rejected(self):
        with self.assertRaises(r.ReminderError):r.validate_root(self.root/'missing')

    def test_cli_register_status_then_outbox(self):
        self.file_json(make_item())
        code, result=self.call('register','--file',str(self.file))
        self.assertEqual(code,0)
        self.assertEqual(result['item_state'],'active')
        code, status=self.call('list')
        self.assertEqual(status['items'][0]['status'],'active')

    def test_cli_rejects_unknown_operation(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:r.main(['--state-dir',str(self.root),'send'])
        self.assertEqual(raised.exception.code,2)

    def test_cli_no_scheduling_or_network_operation(self):
        source=(Path(__file__).resolve().parents[1]/'scripts/deadline_reminder.py').read_text()
        self.assertNotIn('sub.add_parser("send")',source)
        self.assertNotIn('sub.add_parser("schedule")',source)
        self.assertNotIn('sub.add_parser("cron")',source)

    def test_check_cli_with_injected_time(self):
        self.file_json(make_item())
        self.call('register','--file',str(self.file))
        code,result=self.call('check','--at-utc',NOW.isoformat(timespec='seconds'))
        self.assertEqual(code,0)
        self.assertEqual(result['new_fired_count'],1)

    def test_replay_detects_invalid_early_fire(self):
        self.register()
        journal=self.root/r.JOURNAL
        state=self.state()
        rid=next(iter(state['items']))
        event={'version':1,'seq':2,'event_id':'fire-'+rid[4:],
               'at_utc':(NOW-dt.timedelta(days=1)).isoformat(), 'kind':'fired','reminder_id':rid}
        with journal.open('ab') as f:f.write(r.canonical(event)+b'\n')
        with self.assertRaises(r.ReminderError):r.load_journal(self.root)

    def test_two_items_fired_simultaneously(self):
        self.register(make_item(condition='alpha'))
        self.register(make_item(condition='beta'))
        output=r.run_check(self.root,NOW)
        self.assertEqual(output['new_fired_count'],2)
        self.assertEqual(len(set(output['pending_outbox_ids'])),2)

    def test_journal_write_then_reconcile_no_duplicate(self):
        self.register()
        old_refresh=r.refresh_outbox
        with patch.object(r,'refresh_outbox',side_effect=r.ReminderError('SIMULATED_DERIVED_SAVE_FAILURE')):
            with self.assertRaises(r.ReminderError):r.run_check(self.root,NOW)
        self.assertEqual(self.state()['next_seq'],3)
        output=r.run_check(self.root,NOW+dt.timedelta(minutes=1))
        self.assertEqual(output['new_fired_count'],0)
        self.assertEqual(output['pending_delivery_count'],1)

    def test_registration_file_does_not_mutate(self):
        self.file_json(make_item())
        before=self.file.read_bytes();r.register(self.root,r.read_json(self.file))
        self.assertEqual(self.file.read_bytes(),before)

    def test_same_instant_different_zone_is_identity_conflict(self):
        rid=self.register()['reminder_id']
        with self.assertRaises(r.ReminderError) as raised:
            r.reschedule(self.root,rid,self.due(zone='America/New_York'))
        self.assertEqual(raised.exception.code,'CONFLICTING_IDENTITY')

    def test_failure_recurrence_id_distinct_even_same_second(self):
        first=r.write_failure(self.root,'BAD_JOURNAL',NOW)
        r.write_failure(self.root,'',NOW)
        second=r.write_failure(self.root,'BAD_JOURNAL',NOW)
        self.assertNotEqual(first['occurrences'][0]['occurrence_id'],second['occurrences'][1]['occurrence_id'])

    def test_failure_ledger_unknown_version_rejected(self):
        r.write_failure(self.root,'BAD_JOURNAL',NOW)
        path=self.root/r.FAILURES
        obj=json.loads(path.read_text())
        obj['version']=2
        path.write_text(json.dumps(obj))
        with self.assertRaises(r.ReminderError):r.write_failure(self.root,'',NOW)

    def test_failure_state_fake_open_episode_rejected(self):
        payload={'open_code':'BAD_JOURNAL','occurrences':[]}
        (self.root/r.FAILURES).write_bytes(r.canonical({'version':1,'payload':payload,'sha256':r.digest(payload)}))
        with self.assertRaises(r.ReminderError):r.write_failure(self.root,'',NOW)

    def test_due_event_has_no_message_content(self):
        self.register();r.run_check(self.root,NOW)
        self.assertNotIn('message',self.report())
        self.assertEqual(len(self.report()['outbox']),1)


if __name__=='__main__':
    unittest.main()

