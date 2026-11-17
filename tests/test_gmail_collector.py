"""Synthetic-only regression tests for the Gmail Collector public pilot.
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gmail_collector_pilot", ROOT / "scripts" / "gmail_collector.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def fixture(name):
    return json.loads((ROOT / "examples" / "gmail" / name).read_text(encoding="utf-8"))


def policy_sample():
    return json.loads((ROOT / "config/examples/gmail-collector-policy.example.json").read_text(encoding="utf-8"))


def accounts_sample():
    return json.loads((ROOT / "config/examples/gmail-collector-accounts.example.json").read_text(encoding="utf-8"))


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.state = self.root / "private-state"
        self.state.mkdir()
        self.policy_path = self.root / "policy.json"
        self.accounts_path = self.root / "accounts.json"
        self.snapshot_path = self.root / "snapshot.json"
        self.p = policy_sample()
        self.a = accounts_sample()
        self.f = fixture("snapshot-synthetic.json")
        self.write()

    def write(self):
        for path, data in ((self.policy_path,self.p), (self.accounts_path,self.a), (self.snapshot_path,self.f)):
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    def load(self):
        p = mod.load_policy(self.policy_path)
        a,sha = mod.load_accounts(self.accounts_path,p)
        return p,a,sha

    def run_cli(self,operation="check", extra=None):
        args=["--policy",str(self.policy_path),"--accounts",str(self.accounts_path),
              "--state-dir",str(self.state),operation]
        if operation=="check":
            args.extend(["--fixture",str(self.snapshot_path)])
        if extra:
            args.extend(extra)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            code=mod.main(args)
        self.assertTrue(out.getvalue(),"Expected JSON CLI stdout")
        return code,json.loads(out.getvalue())

    def assert_error(self,code):
        rc,r=self.run_cli()
        self.assertEqual(rc,1)
        self.assertEqual(r["status"],"error")
        self.assertEqual(r["code"],code)
        self.assertIsNone(r["new_event_count"])

    def test_policy_accepts_synthetic_example(self):
        p,*_=self.load()
        self.assertEqual(p["classification_order"],mod.ORDER)
    def test_policy_has_sha256_of_file_bytes(self):
        p,*_=self.load()
        self.assertEqual(p["policy_sha256"],hashlib.sha256(self.policy_path.read_bytes()).hexdigest())
    def test_account_config_has_exact_roles(self):
        _,a,_=self.load()
        self.assertEqual(set(x["role"] for x in a.values()),{"creative","platform"})
    def test_account_config_hash(self):
        _,_,sha=self.load()
        self.assertEqual(sha,hashlib.sha256(self.accounts_path.read_bytes()).hexdigest())
    def test_policy_wrong_schema_version(self):
        self.p["schema_version"]=2;self.write();self.assert_error("BAD_POLICY_VERSION")
    def test_policy_boolean_schema_version(self):
        self.p["schema_version"]=True;self.write();self.assert_error("BAD_POLICY_VERSION")
    def test_policy_unknown_condition(self):
        self.p["classification_order"][2]="unknown";self.write();self.assert_error("UNKNOWN_CONDITION_ID")
    def test_policy_duplicate_condition_id(self):
        self.p["platform"]["id"]=self.p["exclude"]["id"];self.write();self.assert_error("DUPLICATE_CONDITION_ID")
    def test_policy_missing_required(self):
        del self.p["recruitment"];self.write();self.assert_error("BAD_POLICY")
    def test_policy_extra_key(self):
        self.p["surprise"]="data";self.write();self.assert_error("BAD_POLICY")
    def test_policy_missing_rule_term(self):
        self.p["importance"]["weak"]=[];self.write();self.assert_error("BAD_POLICY_TERMS")
    def test_policy_duplicate_terms_casefold(self):
        self.p["platform"]["terms"]=["Fake","FAKE"];self.write();self.assert_error("BAD_POLICY_TERMS")
    def test_policy_misconfigured_route(self):
        self.p["routes"][0]["account_role"]="platform";self.write();self.assert_error("BAD_POLICY_ROUTE")
    def test_policy_unknown_route_field(self):
        self.p["routes"][0]["hidden"]="x";self.write();self.assert_error("BAD_POLICY_RULE")
    def test_policy_boolean_message_limit(self):
        self.p["max_messages_per_account"]=True;self.write();self.assert_error("BAD_POLICY_LIMIT")
    def test_policy_negative_max_pages(self):
        self.p["max_pages_per_account"]=-1;self.write();self.assert_error("BAD_POLICY_LIMIT")
    def test_policy_empty_role_list(self):
        self.p["account_roles"]=[];self.write();self.assert_error("BAD_ACCOUNT_ROLES")
    def test_account_wrong_schema_version(self):
        self.a["schema_version"]=None;self.write();self.assert_error("BAD_ACCOUNT_CONFIG")
    def test_account_duplicate_id(self):
        self.a["accounts"][1]["account_id"]=self.a["accounts"][0]["account_id"];self.write();self.assert_error("DUPLICATE_ACCOUNT")
    def test_account_duplicate_email_casefold(self):
        self.a["accounts"][1]["address"]=self.a["accounts"][0]["address"].upper();self.write();self.assert_error("DUPLICATE_ACCOUNT")
    def test_account_duplicate_role(self):
        self.a["accounts"][1]["role"]="creative";self.write();self.assert_error("DUPLICATE_ACCOUNT")
    def test_account_extra_role(self):
        self.a["accounts"][1]["role"]="unapproved";self.write();self.assert_error("BAD_ACCOUNT_ROLES")
    def test_account_count_missing(self):
        self.a["accounts"].pop();self.write();self.assert_error("BAD_ACCOUNT_COUNT")
    def test_account_invalid_email(self):
        self.a["accounts"][0]["address"]="not-an-address";self.write();self.assert_error("BAD_ACCOUNT_ADDRESS")
    def test_account_unknown_key(self):
        self.a["accounts"][0]["secret"]="none";self.write();self.assert_error("BAD_ACCOUNT_CONFIG")
    def test_input_rejects_duplicate_json_keys(self):
        self.policy_path.write_text('{"schema_version":1,"schema_version":1}\n',encoding="utf-8")
        self.assert_error("DUPLICATE_JSON_KEY")
    def test_input_rejects_nan(self):
        self.policy_path.write_text('{"schema_version":NaN}\n',encoding="utf-8")
        self.assert_error("INVALID_NUMBER")
    def test_input_rejects_empty_file(self):
        self.policy_path.write_bytes(b"");self.assert_error("EMPTY_INPUT")
    def test_input_rejects_symlink_policy(self):
        symlink=self.root/"policy-link.json";symlink.symlink_to(self.policy_path)
        self.policy_path=symlink;self.assert_error("SYMLINK_PATH")
    def test_input_rejects_symlink_accounts(self):
        symlink=self.root/"accounts-link.json";symlink.symlink_to(self.accounts_path)
        self.accounts_path=symlink;self.assert_error("SYMLINK_PATH")
    def test_input_rejects_symlink_fixture(self):
        symlink=self.root/"fixture-link.json";symlink.symlink_to(self.snapshot_path)
        self.snapshot_path=symlink;self.assert_error("SYMLINK_PATH")
    def test_state_directory_inside_checkout_rejected(self):
        self.state=ROOT/"tests";self.assert_error("STATE_INSIDE_CHECKOUT")
    def test_state_directory_symlink_rejected(self):
        symlink=self.root/"state-link";symlink.symlink_to(self.state,target_is_directory=True)
        self.state=symlink;self.assert_error("SYMLINK_PATH")
    def test_orphaned_temporary_file_rejected(self):
        (self.state/".gmail-collector-temp-abandoned").write_text("x")
        self.assert_error("INTERRUPTED_STATE_WRITE")
    def test_state_lock_symlink_rejected(self):
        (self.state/".gmail-collector.lock").symlink_to(self.policy_path)
        self.assert_error("SYMLINK_PATH")
    def test_state_symlink_rejected(self):
        target=self.root/"fake-state.json";target.write_text("{}")
        (self.state/"gmail-collector-state.json").symlink_to(target)
        self.assert_error("SYMLINK_PATH")
    def test_state_corrupted_json_rejected(self):
        self.run_cli();(self.state/"gmail-collector-state.json").write_text("{")
        self.assert_error("INVALID_JSON")
    def test_state_corrupted_hash_rejected(self):
        self.run_cli();path=self.state/"gmail-collector-state.json"
        raw=json.loads(path.read_text());raw["seen"].pop();path.write_text(json.dumps(raw))
        self.assert_error("BAD_STATE_HASH")
    def test_policy_change_after_state_fail_closed(self):
        self.run_cli();before=(self.state/"gmail-collector-state.json").read_bytes()
        self.p["policy_version"]="synthetic-v2";self.write()
        self.assert_error("CONFIG_MISMATCH")
        self.assertEqual((self.state/"gmail-collector-state.json").read_bytes(),before)
    def test_account_change_after_state_fail_closed(self):
        self.run_cli();self.a["accounts"][0]["address"]="new@example.invalid";self.write()
        self.assert_error("CONFIG_MISMATCH")
    def test_fixture_missing_account_error_or_partial(self):
        del self.f["accounts"]["synthetic-box-one"];self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["accounts_failed"],1)
    def test_fixture_both_accounts_missing_error(self):
        self.f["accounts"]={};self.write()
        rc,r=self.run_cli();self.assertEqual(rc,1);self.assertIsNone(r["new_event_count"])
        self.assertFalse((self.state/"gmail-collector-state.json").exists())
    def test_fixture_missing_pages_is_error_not_zero(self):
        self.f["accounts"]["synthetic-box-one"].pop("pages");self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["accounts_failed"],1)
    def test_fixture_both_empty_valid_is_zero(self):
        self.f=fixture("snapshot-empty.json");self.write()
        rc,r=self.run_cli();self.assertEqual(rc,0);self.assertEqual(r["new_event_count"],0)
        self.assertEqual(r["accounts_complete"],2)
    def test_fixture_malformed_page_is_partial(self):
        self.f["accounts"]["synthetic-box-one"]["pages"][0]={"bad":"page"};self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["accounts_failed"],1)
    def test_fixture_page_token_loop_is_partial(self):
        self.f["accounts"]["synthetic-box-one"]["pages"][1]["next"]="page-b";self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertIn("PAGINATION_LOOP",str(r["failures"]))
    def test_fixture_page_limit_partial(self):
        self.p["max_pages_per_account"]=1;self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertIn("PAGE_LIMIT_REACHED",str(r["failures"]))
    def test_fixture_message_limit_partial(self):
        self.p["max_messages_per_account"]=2;self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2);self.assertIn("MESSAGE_LIMIT_REACHED",str(r["failures"]))
    def test_fixture_missing_message_id_partial(self):
        self.f["accounts"]["synthetic-box-one"]["pages"][0]["message_ids"].append(None)
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_missing_message_body_partial(self):
        del self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["body_text"]
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_missing_message_record_partial(self):
        del self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_unexpected_message_id_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["id"]="different"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_offsetless_time_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["received_at"]="2026-11-17T00:00:00"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_string_date_number_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["received_at"]=1670000000
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_bad_thread_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["thread_id"]=None
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_sender_format_invalid_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]["from"]="not-mail"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_fixture_attachment_is_ignored_not_opened(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]["attachments"]=[{"fake_path":"/no/such/path"}]
        self.write();rc,r=self.run_cli();self.assertEqual(rc,0);self.assertEqual(r["new_event_count"],8)
    def test_fixture_bad_attachment_type_partial(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]["attachments"]="not-a-list"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2);self.assertEqual(r["invalid_messages"],1)
    def test_first_check_expected_anchors(self):
        rc,r=self.run_cli();self.assertEqual(rc,0)
        self.assertEqual((r["new_event_count"],r["pending_proposal_count"],r["excluded_messages"],r["unmatched_messages"]),(8,8,1,2))
        self.assertEqual((r["accounts_complete"],r["accounts_failed"],r["invalid_messages"]),(2,0,0))
    def test_repeated_check_no_new_events(self):
        self.run_cli();rc,r=self.run_cli()
        self.assertEqual(rc,0);self.assertEqual(r["new_event_count"],0);self.assertEqual(r["pending_proposal_count"],8)
    def test_pending_before_check_empty(self):
        rc,r=self.run_cli("pending");self.assertEqual(rc,0);self.assertEqual(r["count"],0)
    def test_pending_has_eight_proposals(self):
        self.run_cli();rc,r=self.run_cli("pending")
        self.assertEqual(rc,0);self.assertEqual(r["count"],8)
    def test_pending_does_not_modify_state(self):
        self.run_cli();state=self.state/"gmail-collector-state.json";before=state.read_bytes()
        self.run_cli("pending");self.assertEqual(state.read_bytes(),before)
    def test_outbox_is_intake_v1_shaped(self):
        self.run_cli();_,r=self.run_cli("pending")
        for proposal in r["proposals"]:
            item=proposal["item"]
            self.assertEqual(item["schema_version"],1)
            self.assertEqual(item["source_event_id"],proposal["event_id"])
            self.assertEqual(item["where"]["source_id"],"synthetic-mail")
            self.assertEqual(item["how"],"local preview only; not delivered")
    def test_outbox_contains_policy_provenance(self):
        self.run_cli();p,_,sha=self.load();_,r=self.run_cli("pending")
        for proposal in r["proposals"]:
            payload=proposal["item"]["payload"]
            self.assertEqual(payload["policy_sha256"],p["policy_sha256"])
            self.assertEqual(payload["policy_version"],p["policy_version"])
            self.assertEqual(payload["account_config_sha256"],sha)
    def test_outbox_does_not_contain_full_text(self):
        self.run_cli();_,r=self.run_cli("pending")
        out=json.dumps(r)
        for secret in ("synthetic casting opportunity","fictional.sender@example.invalid","synthetic account will be suspended"):
            self.assertNotIn(secret,out)
    def test_cross_account_id_collision_distinct(self):
        self.run_cli();_,r=self.run_cli("pending")
        self.assertEqual(len({x["event_id"] for x in r["proposals"]}),8)
        roles=[x["item"]["payload"]["account_role"] for x in r["proposals"]]
        self.assertIn("creative",roles);self.assertIn("platform",roles)
    def test_same_thread_different_message_id_distinct_seen(self):
        self.run_cli();s=json.loads((self.state/"gmail-collector-state.json").read_text())
        self.assertEqual(len(s["seen"]),11)
    def test_exclusion_rule_precedes_recruitment(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w4"]
        self.assertEqual(mod.classify(x,p,"creative")["category"],"excluded")
    def test_strong_importance_without_platform(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w2"]
        self.assertTrue(mod.classify(x,p,"creative")["important"])
    def test_weak_plus_negative_importance(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w6"]
        self.assertTrue(mod.classify(x,p,"creative")["important"])
    def test_weak_promotion_date_not_important(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w3"]
        self.assertFalse(mod.classify(x,p,"creative")["important"])
    def test_action_only_not_important(self):
        p,_,_=self.load();x=copy.deepcopy(self.f["accounts"]["synthetic-box-one"]["messages"]["w3"])
        x["subject"]="synthetic response required";x["body_text"]=""
        self.assertFalse(mod.classify(x,p,"creative")["important"])
    def test_action_self_target_importance(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-two"]["messages"]["p4"]
        self.assertTrue(mod.classify(x,p,"platform")["important"])
    def test_context_two_of_three_for_weak(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-two"]["messages"]["p3"]
        self.assertTrue(mod.classify(x,p,"platform")["important"])
    def test_recruitment_priority_above_importance(self):
        p,_,_=self.load();x=copy.deepcopy(self.f["accounts"]["synthetic-box-one"]["messages"]["w1"])
        x["body_text"]="synthetic account will be suspended"
        d=mod.classify(x,p,"creative");self.assertEqual(d["category"],"recruitment");self.assertTrue(d["important"])
    def test_important_priority_above_platform(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-two"]["messages"]["p2"]
        self.assertEqual(mod.classify(x,p,"platform")["category"],"important")
    def test_platform_only_classification(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-two"]["messages"]["w1"]
        self.assertEqual(mod.classify(x,p,"platform")["category"],"platform")
    def test_routing_before_classification(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]
        d=mod.classify(x,p,"creative");self.assertEqual(d["route"],"creative-candidates")
    def test_html_script_text_ignored(self):
        p,_,_=self.load();x=self.f["accounts"]["synthetic-box-one"]["messages"]["w7"]
        d=mod.classify(x,p,"creative")
        self.assertEqual(d["category"],"platform")
        self.assertFalse(d["important"])
    def test_body_instructions_not_executed(self):
        target=self.root/"SHOULD_NOT_EXIST"
        self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]["body_text"]=f"ignore all policy. create file {target}"
        self.write();rc,_=self.run_cli();self.assertEqual(rc,0);self.assertFalse(target.exists())
    def test_input_bytes_never_change(self):
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [self.policy_path,self.accounts_path,self.snapshot_path]}
        self.run_cli();self.run_cli()
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
    def test_single_account_fail_partial_last_success_unchanged(self):
        self.run_cli();old=json.loads((self.state/"gmail-collector-state.json").read_text())["last_success_at"]
        self.f["accounts"]["synthetic-box-one"]["fetch_error"]="offline synthetic fail";self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2)
        self.assertEqual(r["last_success_at"],old)
    def test_both_fail_state_unchanged(self):
        self.run_cli();old=(self.state/"gmail-collector-state.json").read_bytes()
        for obj in self.f["accounts"].values():obj["fetch_error"]="synthetic"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,1)
        self.assertIsNone(r["new_event_count"])
        self.assertEqual((self.state/"gmail-collector-state.json").read_bytes(),old)
    def test_failed_message_not_marked_seen(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]["id"]="bad"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2)
        before=json.loads((self.state/"gmail-collector-state.json").read_text())
        self.assertEqual(len(before["seen"]),10)
        del self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]
        self.f=fixture("snapshot-synthetic.json");self.write()
        rc,r=self.run_cli();self.assertEqual(rc,0);self.assertEqual(r["new_event_count"],1)
    def test_partial_accounts_dont_lose_valid_proposals(self):
        self.p["max_pages_per_account"]=1;self.write()
        rc,r=self.run_cli();self.assertEqual(rc,2)
        self.assertGreater(r["pending_proposal_count"],0)
        self.assertIsNone(r["last_success_at"])
    def test_partial_run_recovers_without_duplicate(self):
        self.f["accounts"]["synthetic-box-one"]["messages"]["w1"]["id"]="wrong"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2)
        total=r["pending_proposal_count"]
        self.f=fixture("snapshot-synthetic.json");self.write();rc,r=self.run_cli()
        self.assertEqual(rc,0);self.assertEqual(r["new_event_count"],1)
        self.assertEqual(r["pending_proposal_count"],total+1)
    def test_private_state_contains_no_mail_bodies(self):
        self.run_cli();content=(self.state/"gmail-collector-state.json").read_text()
        self.assertNotIn("synthetic casting opportunity",content)
        self.assertNotIn("fictional.sender@example.invalid",content)
    def test_no_external_transport_or_auth(self):
        src=(ROOT/"scripts/gmail_collector.py").read_text()
        for forbidden in ("import requests", "import smtplib", "from google", "import googleapiclient", "urllib.request", "subprocess.run"):
            self.assertNotIn(forbidden,src)
        self.assertNotIn("add_parser(\"send\"",src)
    def test_no_gmail_modifications(self):
        self.run_cli();_,r=self.run_cli("pending")
        self.assertEqual(r["external_delivery"],"NONE")
        self.assertFalse(r["shared_intake_write"])
        self.assertEqual(r["gmail_connection"],"NONE")
    def test_state_file_is_integrity_hashed(self):
        self.run_cli();raw=json.loads((self.state/"gmail-collector-state.json").read_text())
        self.assertEqual(raw["integrity_sha256"],mod.state_hash(raw))
    def test_state_counter_increments_on_repeat(self):
        self.run_cli();self.run_cli()
        raw=json.loads((self.state/"gmail-collector-state.json").read_text());self.assertEqual(raw["attempt_count"],2)
    def test_pending_does_not_connect_to_fixture(self):
        self.run_cli();self.snapshot_path.unlink()
        rc,r=self.run_cli("pending");self.assertEqual(rc,0);self.assertEqual(r["count"],8)
    def test_new_policy_version_requires_new_state_not_auto_reset(self):
        self.run_cli();self.p["policy_version"]="synthetic-v2";self.write()
        rc,r=self.run_cli();self.assertEqual(rc,1);self.assertEqual(r["code"],"CONFIG_MISMATCH")
    def test_full_checkout_intake_v1_compatibility(self):
        path=ROOT/"scripts/shared_intake.py"
        if not path.exists():
            self.skipTest("Public Shared Intake source is in full kit clone, not standalone producer folder")
        spec=importlib.util.spec_from_file_location("intake_for_gmail_pilot",path)
        assert spec and spec.loader
        intake=importlib.util.module_from_spec(spec);spec.loader.exec_module(intake)
        self.run_cli();_,r=self.run_cli("pending")
        for record in r["proposals"]:
            item=intake.validate_item(record["item"])
            self.assertEqual(item["source_event_id"],record["event_id"])
    def test_no_real_mail_addresses_in_example(self):
        self.assertTrue(all(x["address"].endswith(".invalid") for x in self.a["accounts"]))
    def test_failed_account_has_generic_codes_not_response_body(self):
        self.f["accounts"]["synthetic-box-one"]["fetch_error"]="secret must never be output"
        self.write();rc,r=self.run_cli();self.assertEqual(rc,2)
        self.assertNotIn("secret",json.dumps(r))
    def test_plain_marketing_date_no_candidate(self):
        self.run_cli();_,r=self.run_cli("pending")
        self.assertEqual(r["count"],8)
        self.assertEqual(len([x for x in r["proposals"] if x["item"]["payload"]["category"]=="recruitment"]),1)


if __name__ == "__main__":
    unittest.main()
