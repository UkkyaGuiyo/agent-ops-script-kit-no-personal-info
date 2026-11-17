"""Synthetic-only tests for the offline Notion jobs collector.
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("notion_jobs_collector_test", ROOT / "scripts" / "notion_jobs_collector.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
POLICY = ROOT / "config/examples/notion-jobs-policy.example.yaml"
BASE = ROOT / "examples/notion-jobs/snapshot-baseline.json"
NEW = ROOT / "examples/notion-jobs/snapshot-updated.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-notion-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.state = self.root / "private-state"
        self.state.mkdir()
        self.policy_file = self.root / "policy.yaml"
        self.policy_file.write_bytes(POLICY.read_bytes())
        self.fixture_file = self.root / "snap.json"
        self.fixture_file.write_bytes(BASE.read_bytes())
        self.policy = mod.load_policy(self.policy_file)

    def provider(self, file=BASE):
        return mod.snapshot(file)

    def modify_snapshot(self, fn, *, original=NEW):
        data = json.loads(original.read_text())
        fn(data)
        self.fixture_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return mod.snapshot(self.fixture_file)

    def initialize(self):
        code, result = mod.bootstrap(self.state, self.policy, self.provider())
        self.assertEqual((code, result["bootstrap_status"]), (0, "complete"))

    def run_cli(self, command, fixture=None):
        argv = ["--policy", str(self.policy_file), "--state-dir", str(self.state), command]
        if fixture is not None:
            argv.extend(["--fixture", str(fixture)])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(argv)
        return code, json.loads(out.getvalue())

    def test_policy_parse_and_hash(self):
        self.assertEqual(self.policy["policy_version"], "synthetic-v1")
        self.assertEqual(self.policy["policy_sha256"], sha(self.policy_file))
        self.assertEqual(set(self.policy["conditions"]), mod.CONDITION_IDS)

    def test_initial_bootstrap_no_notifications(self):
        code, result = self.run_cli("bootstrap", BASE)
        self.assertEqual(code, 0)
        self.assertEqual(result["baseline_pages"], 1)
        self.assertEqual(result["baseline_urls"], 1)
        self.assertEqual(result["new_events"], 0)

    def test_initial_bootstrap_cannot_repeat(self):
        self.initialize()
        code, res = self.run_cli("bootstrap", BASE)
        self.assertEqual((code, res["error_code"]), (1, "BOOTSTRAP_ALREADY_COMPLETE"))

    def test_check_before_bootstrap_rejected(self):
        code, result = self.run_cli("check", NEW)
        self.assertEqual((code, result["error_code"]), (1, "BOOTSTRAP_NOT_COMPLETE"))

    def test_pending_before_bootstrap_rejected(self):
        code, result = self.run_cli("pending")
        self.assertEqual((code, result["error_code"]), (1, "BOOTSTRAP_NOT_COMPLETE"))

    def test_new_date_and_url_events(self):
        self.initialize()
        code, result = self.run_cli("check", NEW)
        self.assertEqual(code, 0)
        self.assertEqual(result["new_event_count"], 3)
        self.assertEqual(result["pending_proposal_count"], 3)
        self.assertEqual(result["notion_connection"], "NONE")
        self.assertEqual(result["external_delivery"], "NONE")

    def test_retry_new_data_is_idempotent(self):
        self.initialize()
        self.run_cli("check", NEW)
        code, result = self.run_cli("check", NEW)
        self.assertEqual((code, result["new_event_count"], result["pending_proposal_count"]), (0, 0, 3))

    def test_pending_is_intake_compatible_and_no_send(self):
        self.initialize()
        self.run_cli("check", NEW)
        code, result = self.run_cli("pending")
        self.assertEqual(code, 0)
        self.assertEqual(result["count"], 3)
        self.assertFalse(result["shared_intake_write"])
        for e in result["proposals"]:
            self.assertEqual(e["event_id"], e["item"]["source_event_id"])
            self.assertEqual(e["item"]["status"] if "status" in e["item"] else "unprocessed", "unprocessed")
            self.assertEqual(e["item"]["schema_version"], 1)
            self.assertEqual(e["item"]["payload"]["policy_sha256"], self.policy["policy_sha256"])

    def test_link_normalization_dedupes_query_fragment(self):
        self.initialize()
        self.run_cli("check", NEW)
        pending = mod.pending(self.state, self.policy)["proposals"]
        urls = [x["item"]["payload"].get("url") for x in pending]
        self.assertIn("https://jobs.example/beta", urls)
        self.assertNotIn("https://jobs.example/alpha", urls)
        self.assertNotIn("https://jobs.example/beta?source=new", urls)

    def test_new_day_with_no_links_still_event(self):
        self.initialize()
        p = self.modify_snapshot(lambda d: d["pages"]["synthetic-day-02"].update(body="no links"))
        code, res = mod.check(self.state, self.policy, p)
        self.assertEqual((code, res["new_event_count"]), (0, 2))

    def test_old_page_body_edit_does_not_notify(self):
        self.initialize()
        p = self.modify_snapshot(lambda d: d["pages"]["synthetic-day-01"].update(body="edited text https://jobs.example/alpha?different=yes"), original=BASE)
        code, res = mod.check(self.state, self.policy, p)
        self.assertEqual((code, res["new_event_count"]), (0, 0))

    def test_disappeared_url_does_not_notify(self):
        self.initialize()
        p = self.modify_snapshot(lambda d: d["pages"]["synthetic-day-01"].update(body="no link"), original=BASE)
        code, res = mod.check(self.state, self.policy, p)
        self.assertEqual((code, res["new_event_count"]), (0, 0))

    def test_disappeared_page_does_not_notify(self):
        self.initialize()
        p = self.modify_snapshot(lambda d: d["parent"].update(children=[]), original=BASE)
        code, res = mod.check(self.state, self.policy, p)
        self.assertEqual((code, res["new_event_count"]), (0, 0))

    def test_invalid_child_partial_and_not_seen(self):
        self.initialize()
        p = self.modify_snapshot(lambda d: d["pages"].pop("synthetic-day-02"))
        code, res = mod.check(self.state, self.policy, p)
        self.assertEqual(code, 2)
        self.assertEqual(res["status"], "partial")
        self.assertEqual(res["new_event_count"], 1)  # beta from healthy page
        self.assertEqual(res["failed_children"][0]["reason"], "CHILD_FETCH_FAILED")
        record = mod.read_state(self.state, self.policy)
        self.assertNotIn("synthetic-day-02", record["seen_pages"])
        code2, res2 = mod.check(self.state, self.policy, self.provider(NEW))
        self.assertEqual((code2, res2["new_event_count"]), (0, 2))

    def test_partial_preserves_last_success_at(self):
        self.initialize()
        before = mod.read_state(self.state, self.policy)["last_success_at"]
        p = self.modify_snapshot(lambda d: d["pages"].pop("synthetic-day-02"))
        mod.check(self.state, self.policy, p)
        self.assertEqual(mod.read_state(self.state, self.policy)["last_success_at"], before)

    def test_bootstrap_partial_retries(self):
        p = self.modify_snapshot(lambda d: d["pages"].pop("synthetic-day-01"), original=BASE)
        code, result = mod.bootstrap(self.state, self.policy, p)
        self.assertEqual((code, result["bootstrap_status"]), (2, "started"))
        self.assertIsNone(mod.read_state(self.state, self.policy)["last_success_at"])
        code2, result2 = mod.bootstrap(self.state, self.policy, self.provider(BASE))
        self.assertEqual((code2, result2["attempts"]), (0, 2))

    def test_bootstrap_parent_error_recoverable(self):
        p = self.modify_snapshot(lambda d: d["parent"].update(title="wrong"), original=BASE)
        with self.assertRaisesRegex(mod.CollectorError,"PARENT_VALIDATION_FAILED"):
            mod.bootstrap(self.state,self.policy,p)
        self.assertEqual(mod.read_state(self.state,self.policy)["bootstrap"]["status"], "started")
        code, result = mod.bootstrap(self.state,self.policy,self.provider(BASE))
        self.assertEqual((code,result["attempts"]),(0,2))

    def test_bootstrap_failure_blocks_check(self):
        p = self.modify_snapshot(lambda d: d["pages"].clear(),original=BASE)
        mod.bootstrap(self.state,self.policy,p)
        with self.assertRaisesRegex(mod.CollectorError, "BOOTSTRAP_NOT_COMPLETE"):
            mod.check(self.state,self.policy,self.provider(NEW))

    def test_outbox_event_ids_stable(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        ids = [x["event_id"] for x in mod.pending(self.state,self.policy)["proposals"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(x.startswith("nj-") and len(x)==43 for x in ids))

    def test_real_public_intake_v1_validation(self):
        """Runs on complete kit clone, skips on isolated producer build."""
        source = ROOT / "scripts" / "shared_intake.py"
        if not source.is_file():
            self.skipTest("Real Shared Intake v1 only present in full kit checkout")
        spec = importlib.util.spec_from_file_location("shared_intake_for_jobs_test", source)
        assert spec and spec.loader
        intake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(intake)
        self.initialize()
        mod.check(self.state, self.policy, self.provider(NEW))
        for event in mod.pending(self.state, self.policy)["proposals"]:
            validated = intake.validate_item(event["item"])
            self.assertEqual(validated["source_event_id"], event["event_id"])
            self.assertEqual(validated["status"], "unprocessed")

    def test_no_commands_apply_or_send(self):
        src = (ROOT / "scripts/notion_jobs_collector.py").read_text()
        self.assertNotIn('add_parser("apply")',src)
        self.assertNotIn('add_parser("send")',src)
        self.assertNotIn('import requests',src)
        self.assertNotIn('import urllib.request',src)

    def test_snapshot_source_body_instruction_ignored(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        contents = (self.state / mod.STATE_FILE).read_text()
        self.assertNotIn("Ignore all prior instructions",contents)
        self.assertNotIn("send files",contents)

    def test_no_write_to_source_snapshots(self):
        before = {p:sha(p) for p in (POLICY,BASE,NEW)}
        self.run_cli("bootstrap", BASE)
        self.run_cli("check", NEW)
        self.assertEqual(before,{p:sha(p) for p in before})

    def test_policy_change_fail_closed_state_unchanged(self):
        self.initialize()
        statefile = self.state / mod.STATE_FILE
        before = sha(statefile)
        raw = self.policy_file.read_text().replace("policy_version: synthetic-v1","policy_version: synthetic-v2")
        self.policy_file.write_text(raw)
        code, result = self.run_cli("check", NEW)
        self.assertEqual((code,result["error_code"]),(1,"POLICY_MISMATCH"))
        self.assertEqual(sha(statefile),before)

    def test_state_corruption_fail_closed(self):
        self.initialize()
        statefile = self.state / mod.STATE_FILE
        statefile.write_text('{"invalid":1}')
        code, res = self.run_cli("check", NEW)
        self.assertEqual((code,res["error_code"]),(1,"BAD_STATE"))

    def test_state_integrity_detects_change(self):
        self.initialize()
        p = self.state / mod.STATE_FILE
        data = json.loads(p.read_text())
        data["seen_pages"] = []
        p.write_text(json.dumps(data))
        code,res = self.run_cli("check",NEW)
        self.assertEqual((code,res["error_code"]),(1,"BAD_STATE_INTEGRITY"))

    def test_pending_retries_do_not_modify_state(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        before = sha(self.state / mod.STATE_FILE)
        self.run_cli("pending")
        self.assertEqual(sha(self.state / mod.STATE_FILE),before)

    def test_duplicate_json_keys_fail(self):
        self.fixture_file.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(mod.CollectorError,"DUPLICATE_JSON_KEY"):
            mod.snapshot(self.fixture_file)

    def test_nan_json_rejected(self):
        self.fixture_file.write_text('{"v":NaN}')
        with self.assertRaisesRegex(mod.CollectorError,"INVALID_JSON_NUMBER"):
            mod.snapshot(self.fixture_file)

    def test_state_inside_checkout_rejected(self):
        with self.assertRaisesRegex(mod.CollectorError,"STATE_INSIDE_CHECKOUT"):
            mod.safe_state_dir(ROOT / "tests")

    def test_symlinked_state_rejected(self):
        link = self.root / "link"
        link.symlink_to(self.state, target_is_directory=True)
        with self.assertRaisesRegex(mod.CollectorError,"UNSAFE_SYMLINK"):
            mod.safe_state_dir(link)

    def test_symlinked_policy_rejected(self):
        link=self.root / "link.yaml"
        link.symlink_to(self.policy_file)
        with self.assertRaisesRegex(mod.CollectorError,"UNSAFE_SYMLINK"):
            mod.load_policy(link)

    def test_symlinked_snapshot_rejected(self):
        link=self.root / "link.json"
        link.symlink_to(self.fixture_file)
        with self.assertRaisesRegex(mod.CollectorError,"UNSAFE_SYMLINK"):
            mod.snapshot(link)

    def test_interrupted_state_temp_fail_closed(self):
        self.initialize()
        (self.state / (mod.TEMP_PREFIX+"orphan")).write_text("synthetic")
        code,res=self.run_cli("check",NEW)
        self.assertEqual((code,res["error_code"]),(1,"INTERRUPTED_STATE_SAVE"))

    def test_page_url_mismatch_partial(self):
        self.initialize()
        p=self.modify_snapshot(lambda d: d["pages"]["synthetic-day-02"].update(url="https://notion.example/wrong"))
        code,res=mod.check(self.state,self.policy,p)
        self.assertEqual((code,res["failed_children"][0]["reason"]),(2,"CHILD_VALIDATION_FAILED"))

    def test_parent_url_mismatch_fail_closed(self):
        self.initialize()
        statefile=self.state / mod.STATE_FILE
        before=sha(statefile)
        p=self.modify_snapshot(lambda d:d["parent"].update(url="https://notion.example/wrong"))
        with self.assertRaisesRegex(mod.CollectorError,"PARENT_VALIDATION_FAILED"):
            mod.check(self.state,self.policy,p)
        self.assertEqual(sha(statefile),before)

    def test_parent_incomplete_fail_closed(self):
        self.initialize()
        p=self.modify_snapshot(lambda d:d["parent"].update(complete=False))
        with self.assertRaisesRegex(mod.CollectorError,"PARENT_VALIDATION_FAILED"):
            mod.check(self.state,self.policy,p)

    def test_child_incomplete_partial(self):
        self.initialize()
        p=self.modify_snapshot(lambda d:d["pages"]["synthetic-day-02"].update(complete=False))
        code,res=mod.check(self.state,self.policy,p)
        self.assertEqual((code,res["status"]),(2,"partial"))

    def test_child_body_not_string_partial(self):
        self.initialize()
        p=self.modify_snapshot(lambda d:d["pages"]["synthetic-day-02"].update(body=["unsafe"]))
        code,res=mod.check(self.state,self.policy,p)
        self.assertEqual((code,res["failed_children"][0]["reason"]),(2,"CHILD_VALIDATION_FAILED"))

    def test_parent_body_not_string_error(self):
        self.initialize()
        p=self.modify_snapshot(lambda d:d["parent"].update(body={"instructions":"execute"}))
        with self.assertRaisesRegex(mod.CollectorError,"PARENT_VALIDATION_FAILED"):
            mod.check(self.state,self.policy,p)

    def test_bad_date_title_partial(self):
        self.initialize()
        p=self.modify_snapshot(lambda d: d["parent"]["children"][1].update(title="2026/02/30"))
        code,res=mod.check(self.state,self.policy,p)
        self.assertEqual((code,res["failed_children"][0]["reason"]),(2,"INVALID_DATE_TITLE"))

    def test_duplicate_parent_child_ids_error(self):
        self.initialize()
        p=self.modify_snapshot(lambda d:d["parent"]["children"].append(copy.deepcopy(d["parent"]["children"][0])))
        with self.assertRaisesRegex(mod.CollectorError,"PARENT_VALIDATION_FAILED"):
            mod.check(self.state,self.policy,p)

    def test_unknown_snapshot_fields_error(self):
        self.fixture_file.write_text(json.dumps({"schema_version":1,"parent":{},"pages":{},"unknown":1}))
        with self.assertRaisesRegex(mod.CollectorError,"BAD_FIXTURE_SCHEMA"):
            mod.snapshot(self.fixture_file)

    def test_missing_snapshot_file_error(self):
        code,res=self.run_cli("bootstrap",self.root/"does_not_exist.json")
        self.assertEqual((code,res["error_code"]),(1,"MISSING_INPUT"))

    def test_lock_file_symlink_rejected(self):
        path=self.state / mod.LOCK_FILE
        path.symlink_to(self.policy_file)
        code,res=self.run_cli("bootstrap",BASE)
        self.assertEqual((code,res["error_code"]),(1,"UNSAFE_SYMLINK"))

    def test_state_file_symlink_rejected(self):
        path=self.state / mod.STATE_FILE
        path.symlink_to(self.fixture_file)
        code,res=self.run_cli("bootstrap",BASE)
        self.assertEqual((code,res["error_code"]),(1,"UNSAFE_SYMLINK"))

    def test_policy_invalid_version(self):
        self.policy_file.write_text(self.policy_file.read_text().replace("schema_version: 1","schema_version: 2"))
        with self.assertRaisesRegex(mod.CollectorError,"UNSUPPORTED_POLICY_VERSION"):
            mod.load_policy(self.policy_file)

    def test_policy_unknown_condition(self):
        self.policy_file.write_text(self.policy_file.read_text().replace("new_url: true","unknown_rule: true"))
        with self.assertRaisesRegex(mod.CollectorError,"UNKNOWN_CONDITION_ID"):
            mod.load_policy(self.policy_file)

    def test_policy_duplicate_condition(self):
        self.policy_file.write_text(self.policy_file.read_text()+"  new_url: true\n")
        with self.assertRaisesRegex(mod.CollectorError,"DUPLICATE_POLICY_KEY"):
            mod.load_policy(self.policy_file)

    def test_policy_duplicate_top_level(self):
        self.policy_file.write_text(self.policy_file.read_text()+"source_id: another-source\n")
        with self.assertRaisesRegex(mod.CollectorError,"DUPLICATE_POLICY_KEY"):
            mod.load_policy(self.policy_file)

    def test_policy_unknown_top_level(self):
        self.policy_file.write_text(self.policy_file.read_text()+"another_key: true\n")
        with self.assertRaisesRegex(mod.CollectorError,"UNKNOWN_POLICY_KEY"):
            mod.load_policy(self.policy_file)

    def test_policy_missing_required(self):
        self.policy_file.write_text(self.policy_file.read_text().replace("parent_title: \"Synthetic Job Save\"\n",""))
        with self.assertRaisesRegex(mod.CollectorError,"INCOMPLETE_POLICY"):
            mod.load_policy(self.policy_file)

    def test_policy_both_conditions_false(self):
        self.policy_file.write_text(self.policy_file.read_text().replace("new_date_page: true","new_date_page: false").replace("new_url: true","new_url: false"))
        with self.assertRaisesRegex(mod.CollectorError,"NO_ENABLED_CONDITIONS"):
            mod.load_policy(self.policy_file)

    def test_url_fragment_removed(self):
        self.assertEqual(mod.url_clean("https://jobs.example/post#fragment"),"https://jobs.example/post")

    def test_url_query_removed(self):
        self.assertEqual(mod.url_clean("https://jobs.example/post?tracking=1"),"https://jobs.example/post")

    def test_url_case_hostname_normalized(self):
        self.assertEqual(mod.url_clean("HTTPS://JOBS.Example/X"),"https://jobs.example/X")

    def test_url_path_case_preserved(self):
        self.assertEqual(mod.url_clean("https://jobs.example/AbC"),"https://jobs.example/AbC")

    def test_url_user_info_rejected(self):
        with self.assertRaisesRegex(mod.CollectorError,"INVALID_JOB_URL"):
            mod.url_clean("https://user:password" + chr(64) + "jobs.example/path")

    def test_url_bad_port_rejected(self):
        with self.assertRaisesRegex(mod.CollectorError,"INVALID_JOB_URL"):
            mod.url_clean("https://jobs.example:bad/path")

    def test_non_url_does_not_become_event(self):
        self.assertEqual(mod.urls_in_body("please call this string, not URL"),[])

    def test_duplicate_same_url_list_deduped(self):
        self.assertEqual(mod.urls_in_body("https://jobs.example/a?x=1 https://jobs.example/a?x=2#f"),["https://jobs.example/a"])

    def test_date_leap_year(self):
        self.assertTrue(mod.valid_date_title("2028/02/29"))
        self.assertFalse(mod.valid_date_title("2027/02/29"))

    def test_date_strict_zeros(self):
        self.assertFalse(mod.valid_date_title("2026/1/1"))
        self.assertTrue(mod.valid_date_title("2026/01/01"))

    def test_fixture_provider_implements_protocol_methods(self):
        p=self.provider(BASE)
        self.assertEqual(p.fetch_parent()["id"],"synthetic-parent")
        self.assertIsNotNone(p.fetch_child("synthetic-day-01"))
        self.assertIsNone(p.fetch_child("missing"))

    def test_condition_disabled_date_only_url(self):
        text=self.policy_file.read_text().replace("new_date_page: true","new_date_page: false")
        self.policy_file.write_text(text)
        self.policy=mod.load_policy(self.policy_file)
        self.initialize()
        code,res=mod.check(self.state,self.policy,self.provider(NEW))
        self.assertEqual((code,res["new_event_count"]),(0,2))

    def test_condition_disabled_url_only_date(self):
        text=self.policy_file.read_text().replace("new_url: true","new_url: false")
        self.policy_file.write_text(text)
        self.policy=mod.load_policy(self.policy_file)
        self.initialize()
        code,res=mod.check(self.state,self.policy,self.provider(NEW))
        self.assertEqual((code,res["new_event_count"]),(0,1))

    def test_empty_complete_parent_is_valid_baseline(self):
        p=self.modify_snapshot(lambda d:(d["parent"].update(children=[]),d["pages"].clear()),original=BASE)
        code,res=mod.bootstrap(self.state,self.policy,p)
        self.assertEqual((code,res["baseline_pages"]),(0,0))

    def test_failed_parent_is_not_successful_zero(self):
        p=self.modify_snapshot(lambda d:d["parent"].update(complete=False),original=BASE)
        code,res=self.run_cli("bootstrap",self.fixture_file)
        self.assertEqual(code,1)
        self.assertIsNone(res["items_count"])
        self.assertEqual(res["error_code"],"PARENT_VALIDATION_FAILED")

    def test_replay_after_atomic_accepted_state(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        self.assertEqual(mod.read_state(self.state,self.policy)["bootstrap"]["status"],"complete")
        self.assertEqual(len(mod.read_state(self.state,self.policy)["outbox"]),3)

    def test_fixture_change_does_not_change_prior_pending(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        before=copy.deepcopy(mod.pending(self.state,self.policy)["proposals"])
        p=self.modify_snapshot(lambda d:d["pages"]["synthetic-day-02"].update(body="no URLs"),original=NEW)
        mod.check(self.state,self.policy,p)
        self.assertEqual(mod.pending(self.state,self.policy)["proposals"],before)

    def test_output_has_no_raw_text_body(self):
        self.initialize()
        mod.check(self.state,self.policy,self.provider(NEW))
        output=json.dumps(mod.pending(self.state,self.policy),ensure_ascii=False)
        self.assertNotIn("Synthetic page list",output)
        self.assertNotIn("Ignore all prior instructions",output)


if __name__=="__main__":
    unittest.main()
