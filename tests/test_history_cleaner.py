"""Synthetic tests for the read-only public Shared Intake v1 retention preview.
Copyright (C) 2026 Contributors to Agent Ops Script Kit
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

CODE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "history_cleaner.py"
SPEC = importlib.util.spec_from_file_location("history_cleaner", CODE)
hc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hc)
UTC = dt.timezone.utc
NOW = dt.datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
CUTOFF = NOW - dt.timedelta(days=90)


def iso(instant):
    return instant.isoformat(timespec="seconds")


class HistoryCleanerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="history-cleaner-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.root = self.base / "intake"
        self.root.mkdir()
        (self.root / ".intake.lock").write_bytes(b"")
        (self.root / "events").mkdir()
        self.roles = self.base / "roles.json"
        self.set_roles({"synthetic-source": "general", "synthetic-reminder": "reminder"})
        self.events = []

    def set_roles(self, roles):
        self.roles.write_text(json.dumps({"version": 1, "source_roles": roles}), encoding="utf-8")

    def event(self, kind, when, **data):
        rec = {"schema_version": 1, "seq": len(self.events) + 1,
               "occurred_at": iso(when), "event_id": f"evt-{len(self.events) + 1}", "kind": kind, **data}
        self.events.append(rec)
        return rec

    def add_item(self, ident="item-1", source="synthetic-source", when=None, source_event="original-1"):
        self.event("item_added", when or CUTOFF - dt.timedelta(hours=3),
                   item={"schema_version": 1, "item_id": ident, "where": {"source_id": source},
                         "when_fetched": iso(when or CUTOFF - dt.timedelta(hours=3)),
                         "source_event_id": source_event, "status": "unprocessed"})

    def transition(self, new="reported", ident="item-1", when=CUTOFF, old="unprocessed"):
        self.event("item_transition", when, item_id=ident, from_state=old, to_state=new)

    def run_start(self, run_id="r-1", when=None, source="synthetic-source"):
        self.event("source_run_started", when or CUTOFF, source_id=source, run_id=run_id)

    def run_error(self, run_id="r-1", when=None):
        self.event("source_run_error", when or CUTOFF, source_id="synthetic-source",
                   run_id=run_id, error_code="SYNTHETIC_FAILURE")

    def run_finish(self, run_id="r-1", when=None):
        self.event("source_run_completed", when or CUTOFF, source_id="synthetic-source",
                   run_id=run_id, outcome="success")

    def save(self):
        for path in (self.root / "events").glob("*"):
            path.unlink()
        days = {}
        for rec in self.events:
            day = str(rec["occurred_at"])[:10]
            days.setdefault(day, []).append(rec)
        for day, records in days.items():
            (self.root / "events" / (day + ".jsonl")).write_bytes(
                b"".join(json.dumps(x, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode() + b"\n" for x in records))

    def sample(self, role="synthetic-source", at=CUTOFF, terminal="reported"):
        self.add_item(source=role)
        if terminal == "reported":
            self.transition("audited", when=at-dt.timedelta(seconds=1), old="unprocessed")
            self.transition("reported", when=at, old="audited")
        else:
            self.transition(terminal, when=at)
        self.save()

    def preview(self, days=90, now=NOW):
        return hc.preview(self.root, hc.load_policy(self.roles), days=days, as_of=now)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(CODE), "--data-dir", str(self.root),
                               "--source-roles", str(self.roles), "--as-of", iso(NOW), *args],
                              text=True, capture_output=True, check=False)

    def hash_snapshot(self):
        return {str(p.relative_to(self.root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file()}

    def test_terminal_exact_90_days_candidate(self):
        self.sample()
        r = self.preview()
        self.assertEqual((r["counts"]["candidate"], r["status"]), (1, "preview"))

    def test_terminal_one_second_under_90_days_not_due(self):
        self.sample(at=CUTOFF + dt.timedelta(seconds=1))
        self.assertEqual(self.preview()["item_previews"][0]["decision"], "not_due")

    def test_terminal_one_second_past_threshold_candidate(self):
        self.sample(at=CUTOFF - dt.timedelta(seconds=1))
        self.assertEqual(self.preview()["item_previews"][0]["decision"], "candidate")

    def test_cutoff_respects_custom_days(self):
        self.sample(at=NOW-dt.timedelta(days=14))
        self.assertEqual(self.preview(days=14)["counts"]["candidate"], 1)

    def test_default_cli_90_days(self):
        self.sample()
        self.assertEqual(json.loads(self.cli().stdout)["retention_days"], 90)

    def test_audited_never_candidate(self):
        self.add_item(); self.transition("audited", when=CUTOFF); self.save()
        self.assertEqual(self.preview()["item_previews"][0]["decision"], "excluded")

    def test_unprocessed_never_candidate(self):
        self.add_item(); self.save()
        self.assertEqual(self.preview()["item_previews"][0]["decision"], "excluded")

    def test_discarded_terminal_candidate(self):
        self.sample(terminal="discarded")
        self.assertEqual(self.preview()["counts"]["candidate"], 1)

    def test_terminal_start_clock_not_registration(self):
        self.sample(at=NOW-dt.timedelta(days=2))
        self.assertEqual(self.preview()["counts"]["candidate"], 0)

    def test_untagged_origin_hold_after_threshold(self):
        self.sample(role="synthetic-unknown")
        self.assertEqual(self.preview()["item_previews"][0]["reason"], "UNKNOWN_ITEM_ORIGIN")

    def test_untagged_origin_before_threshold_not_due(self):
        self.sample(role="synthetic-unknown",at=NOW-dt.timedelta(days=1))
        self.assertEqual(self.preview()["item_previews"][0]["decision"], "not_due")

    def test_reminder_body_is_age_candidate_but_events_protected(self):
        self.sample(role="synthetic-reminder")
        item=self.preview()["item_previews"][0]
        self.assertEqual(item["decision"], "candidate")
        self.assertEqual(len(item["event_ids_protected"]), 3)
        self.assertFalse(item["event_delete_allowed"])

    def test_never_claim_origin_is_independently_verified(self):
        self.sample()
        self.assertFalse(self.preview()["item_previews"][0]["origin_verified_independently"])

    def test_candidate_never_marks_deletion_safe(self):
        self.sample()
        p=self.preview()
        self.assertFalse(p["item_previews"][0]["deletion_safe"])
        self.assertEqual(p["safe_to_delete_count"], 0)

    def test_seen_is_never_marked_independent(self):
        self.sample()
        self.assertFalse(self.preview()["seen_memory_independent"])

    def test_prune_audit_is_not_verified(self):
        self.sample()
        self.assertFalse(self.preview()["prune_prepare_complete_verified"])

    def test_future_terminal_hold(self):
        self.sample(at=NOW + dt.timedelta(days=1))
        self.assertEqual(self.preview()["item_previews"][0]["reason"], "FUTURE_TERMINAL_TIMESTAMP")

    def test_running_run_excluded(self):
        self.run_start(); self.save()
        self.assertEqual(self.preview()["run_previews"][0]["decision"], "excluded")

    def test_completed_run_retention_unconfirmed_hold(self):
        self.run_start(); self.run_finish(); self.save()
        r=self.preview()
        self.assertEqual((r["status"],r["run_held_count"]), ("hold",1))

    def test_error_run_protected_hold(self):
        self.run_start(); self.run_error(); self.run_finish(); self.save()
        r=self.preview()
        self.assertEqual(r["protected_error_event_count"], 1)
        self.assertEqual(r["run_previews"][0]["reason"], "ERROR_AUDIT_PROTECTED")

    def test_run_ids_and_events_remain_protected(self):
        self.run_start(); self.run_finish(); self.save()
        r=self.preview(); self.assertEqual(len(r["run_previews"][0]["event_ids_protected"]),2)

    def test_dry_run_keeps_all_bytes_and_mtimes(self):
        self.sample(); before=self.hash_snapshot(); self.preview(); after=self.hash_snapshot()
        self.assertEqual(before,after)

    def test_cli_dry_run_keeps_all_bytes_and_mtimes(self):
        self.sample(); before=self.hash_snapshot(); p=self.cli(); after=self.hash_snapshot()
        self.assertEqual((p.returncode,before),(0,after))

    def test_cli_holds_exit_2(self):
        self.sample(role="unknown-source")
        p=self.cli(); self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)["status"],"hold")

    def test_cli_error_exit_1(self):
        self.sample(); (self.root/"events"/"2026-02-01.jsonl").write_text("broken\n")
        p=self.cli(); self.assertEqual(p.returncode,1)
        self.assertEqual(json.loads(p.stdout)["status"],"error")

    def test_missing_lock_hold_without_creating_it(self):
        self.sample(); (self.root/".intake.lock").unlink()
        p=self.cli(); self.assertEqual(p.returncode,2)
        self.assertFalse((self.root/".intake.lock").exists())

    def test_missing_journal_error(self):
        (self.root/"events").rmdir()
        with self.assertRaisesRegex(hc.PreviewError,"MISSING_JOURNAL"):
            self.preview()

    def test_empty_journal_hold(self):
        with self.assertRaisesRegex(hc.PreviewHold,"EMPTY_JOURNAL_NO_BASELINE"):
            self.preview()

    def test_interrupted_intake_save_hold(self):
        self.sample(); (self.root/".intake-temp-abc").write_bytes(b"partial")
        with self.assertRaisesRegex(hc.PreviewHold,"INTERRUPTED_INTAKE_SAVE"):
            self.preview()

    def test_prune_log_present_hold(self):
        self.sample(); (self.root/"prune_log.json").write_text("{}")
        with self.assertRaisesRegex(hc.PreviewHold,"UNSUPPORTED_PRUNE_EVIDENCE"):
            self.preview()

    def test_unrecognized_prune_event_error(self):
        self.sample(); self.event("prune_prepare", NOW); self.save()
        with self.assertRaisesRegex(hc.PreviewError,"UNSUPPORTED_EVENT_KIND"):
            self.preview()

    def test_seq_gap_error(self):
        self.sample(); self.events[-1]["seq"]=99; self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_SEQ"):
            self.preview()

    def test_duplicate_event_id_error(self):
        self.sample(); self.events[-1]["event_id"]=self.events[0]["event_id"];self.save()
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_EVENT_ID"):
            self.preview()

    def test_bad_transition_without_item(self):
        self.transition();self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_TRANSITION"):
            self.preview()

    def test_illegal_transition_error(self):
        self.sample();self.transition("audited",when=NOW,old="reported");self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_TRANSITION"):
            self.preview()

    def test_duplicate_item_id_error(self):
        self.add_item();self.add_item(source_event="original-2");self.save()
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_ITEM_ID"):
            self.preview()

    def test_duplicate_source_event_error(self):
        self.add_item();self.add_item(ident="item-2");self.save()
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_SOURCE_EVENT"):
            self.preview()

    def test_bad_day_file_error(self):
        self.sample(); a=next((self.root/"events").glob("*.jsonl"));a.rename(a.with_name("2099-01-01.jsonl"))
        with self.assertRaisesRegex(hc.PreviewError,"EVENT_DAY_MISMATCH"):
            self.preview()

    def test_bad_filename_error(self):
        self.sample(); (self.root/"events"/"bad.txt").write_text("text")
        with self.assertRaisesRegex(hc.PreviewError,"UNEXPECTED_JOURNAL_ENTRY"):
            self.preview()

    def test_partial_journal_line_error(self):
        self.sample(); a=next((self.root/"events").glob("*.jsonl"));a.write_bytes(a.read_bytes().rstrip(b"\n"))
        with self.assertRaisesRegex(hc.PreviewError,"PARTIAL_JOURNAL"):
            self.preview()

    def test_empty_line_error(self):
        self.sample(); a=next((self.root/"events").glob("*.jsonl"));a.write_bytes(a.read_bytes()+b"\n")
        with self.assertRaisesRegex(hc.PreviewError,"EMPTY_JOURNAL_LINE"):
            self.preview()

    def test_bad_json_record_error(self):
        self.sample(); a=next((self.root/"events").glob("*.jsonl"));a.write_bytes(b"not json\n")
        with self.assertRaisesRegex(hc.PreviewError,"INVALID_JSON"):
            self.preview()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_JSON_KEY"):
            hc.strict_json(b'{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(hc.PreviewError,"INVALID_NUMBER"):
            hc.strict_json(b'{"x":NaN}')

    def test_bad_journal_schema_bool_rejected(self):
        self.sample();self.events[0]["schema_version"]=True;self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_JOURNAL_SCHEMA"):
            self.preview()

    def test_event_timestamp_without_offset_rejected(self):
        self.sample();self.events[0]["occurred_at"]="2026-02-01T00:00:00";self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_TIME"):
            self.preview()

    def test_bad_run_error_without_start(self):
        self.run_error();self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_RUN_ERROR"):
            self.preview()

    def test_bad_run_completion_without_start(self):
        self.run_finish();self.save()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_RUN_COMPLETION"):
            self.preview()

    def test_duplicate_run_rejected(self):
        self.run_start();self.run_start();self.save()
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_RUN"):
            self.preview()

    def test_bad_policy_missing_file(self):
        self.roles.unlink()
        with self.assertRaisesRegex(hc.PreviewError,"MISSING_POLICY"):
            hc.load_policy(self.roles)

    def test_bad_policy_bool_version_rejected(self):
        self.roles.write_text('{"version":true,"source_roles":{}}')
        with self.assertRaisesRegex(hc.PreviewError,"BAD_POLICY_SCHEMA"):
            hc.load_policy(self.roles)

    def test_bad_policy_role_rejected(self):
        self.set_roles({"synthetic-source":"maybe"})
        with self.assertRaisesRegex(hc.PreviewError,"BAD_SOURCE_ROLE"):
            hc.load_policy(self.roles)

    def test_bad_policy_duplicate_key_rejected(self):
        self.roles.write_text('{"version":1,"source_roles":{"s":"general","s":"reminder"}}')
        with self.assertRaisesRegex(hc.PreviewError,"DUPLICATE_JSON_KEY"):
            hc.load_policy(self.roles)

    def test_symlinked_journal_rejected(self):
        self.sample();a=next((self.root/"events").glob("*.jsonl"));b=self.base/"real.jsonl";a.rename(b);a.symlink_to(b)
        with self.assertRaisesRegex(hc.PreviewError,"SYMLINK_PATH"):
            self.preview()

    def test_symlinked_policy_rejected(self):
        path=self.base/"real-policy.json";self.roles.rename(path);self.roles.symlink_to(path)
        with self.assertRaisesRegex(hc.PreviewError,"SYMLINK_PATH"):
            hc.load_policy(self.roles)

    def test_public_checkout_root_rejected(self):
        self.sample()
        with mock.patch.object(hc.Path,"resolve", return_value=self.root.parent):
            with self.assertRaisesRegex(hc.PreviewError,"DATA_DIR_IN_PUBLIC_CHECKOUT"):
                self.preview()

    def test_negative_days_rejected(self):
        self.sample()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_RETENTION_DAYS"):
            self.preview(days=-1)

    def test_nonint_days_rejected(self):
        self.sample()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_RETENTION_DAYS"):
            self.preview(days=True)

    def test_excess_days_rejected(self):
        self.sample()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_RETENTION_DAYS"):
            self.preview(days=36501)

    def test_missing_timezone_asof_rejected(self):
        self.sample()
        with self.assertRaisesRegex(hc.PreviewError,"BAD_AS_OF"):
            self.preview(now=dt.datetime(2026,5,1))

    def test_repeated_preview_deterministic(self):
        self.sample();self.assertEqual(self.preview(),self.preview())

    def test_second_item_class_counts(self):
        self.add_item(ident="a-1",source_event="one");self.transition("discarded",ident="a-1")
        self.add_item(ident="b-2",source_event="two",when=CUTOFF+dt.timedelta(seconds=5));self.save()
        p=self.preview();self.assertEqual(p["counts"],{"candidate":1,"not_due":0,"excluded":1,"hold":0})

    def test_generated_output_has_no_apply_authority(self):
        self.sample();p=self.preview();self.assertFalse(p["journal_compaction_authorized"])
        self.assertEqual(p["records_changed"],0)

    def test_help_does_not_advertise_apply(self):
        p=subprocess.run([sys.executable,str(CODE),"--help"],capture_output=True,text=True)
        self.assertEqual(p.returncode,0)
        self.assertNotIn("--apply",p.stdout)

    def test_missing_derived_flag_not_recreated(self):
        self.sample();self.preview()
        self.assertFalse((self.root/"flag.json").exists())

    def test_scope_does_not_touch_other_files(self):
        self.sample();(self.root/"unrelated.txt").write_text("content")
        before=self.hash_snapshot();self.preview();self.assertEqual(before,self.hash_snapshot())

    @unittest.skipUnless(CODE.with_name("shared_intake.py").is_file(),
                         "Full public kit required for end-to-end intake compatibility")
    def test_end_to_end_public_shared_intake_cli(self):
        """When shipped in the full repo, use the REAL v1 writer and transition CLI."""
        source = CODE.with_name("shared_intake.py")
        item = self.base / "input.json"
        item.write_text(json.dumps({
            "schema_version": 1, "item_id": "synthetic-live-item",
            "source_event_id": "synthetic-live-event",
            "where": {"source_id": "synthetic-source"},
            "when_fetched": "2026-01-01T00:00:00+00:00",
            "who": "synthetic", "what": "synthetic", "why": "test", "how": "manual"}), encoding="utf-8")
        def run(*args):
            return subprocess.run([sys.executable, str(source), "--data-dir", str(self.root),
                                   *args], capture_output=True, text=True, check=False)
        self.assertEqual(run("ingest", "--file", str(item)).returncode, 0)
        self.assertEqual(run("transition", "--item-id", "synthetic-live-item",
                             "--to", "audited", "--event-id", "synthetic-audit").returncode, 0)
        self.assertEqual(run("transition", "--item-id", "synthetic-live-item",
                             "--to", "reported", "--event-id", "synthetic-report").returncode, 0)
        before = self.hash_snapshot()
        p = self.cli("--days", "0", "--as-of", "2090-01-01T00:00:00+00:00")
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        parsed = json.loads(p.stdout)
        self.assertEqual(parsed["counts"]["candidate"], 1)
        self.assertEqual(parsed["safe_to_delete_count"], 0)
        self.assertEqual(before, self.hash_snapshot())


if __name__ == "__main__":
    unittest.main()
