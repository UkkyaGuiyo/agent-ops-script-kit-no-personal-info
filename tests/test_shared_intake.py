# Copyright (C) 2026 Contributors to Agent Ops Script Kit
# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic-only public shared-intake tests. No accounts or real records."""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shared_intake as s  # noqa: E402


class SharedIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "private-state"
        self.data.mkdir()
        self.item_file = self.root / "input.json"

    def item(self, event="synthetic-01", **overrides):
        item = {"schema_version": 1, "when_fetched": "2026-11-17T00:00:00+00:00",
                "where": {"source_id": "synthetic-source"}, "source_event_id": event,
                "what": "synthetic event only"}
        item.update(overrides)
        return item

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "shared_intake.py"),
                               "--data-dir", str(self.data), *args], capture_output=True, text=True)

    def test_empty_status_is_not_a_source_run_success(self):
        status = s.status(self.data)
        self.assertEqual(status["last_seq"], 0)
        self.assertEqual(status["source_runs"], [])
        self.assertIn("flag.json:missing", status["derived_warnings"])

    def test_missing_when_fetched(self):
        item = self.item()
        item.pop("when_fetched")
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, item)

    def test_missing_where_source_id(self):
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(where={}))

    def test_timezone_required(self):
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(when_fetched="2026-11-17T00:00:00"))

    def test_unknown_initial_state_rejected(self):
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(status="audited"))

    def test_unknown_schema_rejected(self):
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(schema_version=2))

    def test_item_without_stable_event_or_id_rejected(self):
        item = self.item()
        item.pop("source_event_id")
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, item)

    def test_explicit_item_id_works_without_source_event(self):
        item = self.item(item_id="synthetic-manual-id")
        item.pop("source_event_id")
        self.assertTrue(s.ingest(self.data, item)["added"])

    def test_deterministic_item_id_and_replay(self):
        first = s.ingest(self.data, self.item())
        again = s.ingest(self.data, self.item())
        self.assertTrue(first["added"])
        self.assertFalse(again["added"])
        self.assertEqual(first["item_id"], again["item_id"])
        self.assertEqual(s.status(self.data)["last_seq"], 1)
        journal = list((self.data / "events").glob("*.jsonl"))
        self.assertEqual(len(journal), 1)
        self.assertEqual(len(journal[0].read_text().splitlines()), 1)

    def test_same_id_conflicting_payload_fails(self):
        s.ingest(self.data, self.item())
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(what="changed"))
        self.assertEqual(s.status(self.data)["last_seq"], 1)

    def test_same_source_event_other_explicit_id_rejected(self):
        s.ingest(self.data, self.item())
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item(item_id="different"))

    def test_accepted_only_after_flag_and_state(self):
        value = s.ingest(self.data, self.item())
        self.assertTrue(value["flag"]["raised"])
        flag = json.loads((self.data / "flag.json").read_text())
        self.assertEqual(flag["unprocessed_count"], 1)
        self.assertEqual(json.loads((self.data / "state.json").read_text())["last_seq"], 1)

    def test_flag_write_failure_does_not_ack_and_retry_repairs(self):
        orig = s.atomic_json
        def fail_flag(path, value):
            if path.name == "flag.json":
                raise s.IntakeError("synthetic flag failure")
            orig(path, value)
        with patch.object(s, "atomic_json", side_effect=fail_flag):
            with self.assertRaises(s.IntakeError):
                s.ingest(self.data, self.item())
        self.assertEqual(s.replay(s.load_events(self.data))["next_seq"], 2)
        retry = s.ingest(self.data, self.item())
        self.assertFalse(retry["added"])
        self.assertEqual(json.loads((self.data / "flag.json").read_text())["unprocessed_count"], 1)

    def test_transition_valid_path_and_flag(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        a = s.transition(self.data, identifier, "audited", "transition-1")
        self.assertTrue(a["changed"])
        self.assertEqual(a["flag"]["unprocessed_count"], 0)
        self.assertEqual(a["flag"]["open_count"], 1)
        b = s.transition(self.data, identifier, "reported", "transition-2")
        self.assertTrue(b["changed"])
        self.assertEqual(b["flag"]["open_count"], 0)
        self.assertEqual(s.status(self.data)["status_counts"]["reported"], 1)

    def test_can_discard_from_unprocessed_and_audited(self):
        a = s.ingest(self.data, self.item("one"))["item_id"]
        b = s.ingest(self.data, self.item("two"))["item_id"]
        s.transition(self.data, a, "discarded", "discard-one")
        s.transition(self.data, b, "audited", "audit-two")
        s.transition(self.data, b, "discarded", "discard-two")
        self.assertEqual(s.status(self.data)["status_counts"]["discarded"], 2)

    def test_illegal_transition_fails(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        with self.assertRaises(s.IntakeError):
            s.transition(self.data, identifier, "reported", "skip-audit")

    def test_missing_item_transition_fails(self):
        with self.assertRaises(s.IntakeError):
            s.transition(self.data, "does-not-exist", "audited", "transition-z")

    def test_transition_idempotent_replay(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        s.transition(self.data, identifier, "audited", "same-event")
        self.assertFalse(s.transition(self.data, identifier, "audited", "same-event")["changed"])
        self.assertEqual(s.status(self.data)["last_seq"], 2)

    def test_event_id_reuse_conflict(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        s.transition(self.data, identifier, "audited", "same-event")
        with self.assertRaises(s.IntakeError):
            s.transition(self.data, identifier, "discarded", "same-event")

    def test_terminal_cannot_transition(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        s.transition(self.data, identifier, "discarded", "discard-1")
        with self.assertRaises(s.IntakeError):
            s.transition(self.data, identifier, "audited", "resume-1")

    def test_run_failure_distinct_from_zero_items(self):
        s.run_start(self.data, "synthetic-source", "run-01")
        result = s.run_finish(self.data, "synthetic-source", "run-01", "error")
        self.assertEqual(result["outcome"], "error")
        status = s.status(self.data)
        self.assertEqual(status["last_seq"], 2)
        self.assertEqual(status["source_runs"][0]["outcome"], "error")
        self.assertEqual(status["status_counts"]["unprocessed"], 0)

    def test_separate_source_error_record_and_replay(self):
        s.run_start(self.data, "synthetic-source", "run-error-test")
        first = s.run_error(self.data, "synthetic-source", "run-error-test", "network-1", "FETCH_FAILED")
        second = s.run_error(self.data, "synthetic-source", "run-error-test", "network-1", "FETCH_FAILED")
        self.assertTrue(first["recorded"])
        self.assertFalse(second["recorded"])
        s.run_finish(self.data, "synthetic-source", "run-error-test", "error")
        state = s.status(self.data)
        self.assertEqual(len(state["source_errors"]), 1)
        self.assertEqual(state["source_errors"][0]["error_code"], "FETCH_FAILED")
        self.assertEqual(state["source_runs"][0]["outcome"], "error")

    def test_source_error_without_running_run_fails(self):
        with self.assertRaises(s.IntakeError):
            s.run_error(self.data, "synthetic-source", "not-started", "err-one", "FETCH_FAILED")

    def test_source_error_conflicting_replay_fails(self):
        s.run_start(self.data, "synthetic-source", "run-2")
        s.run_error(self.data, "synthetic-source", "run-2", "err-one", "FETCH_FAILED")
        with self.assertRaises(s.IntakeError):
            s.run_error(self.data, "synthetic-source", "run-2", "err-one", "PARSE_FAILED")

    def test_run_partial_recorded(self):
        s.run_start(self.data, "synthetic-source", "run-02")
        result = s.run_finish(self.data, "synthetic-source", "run-02", "partial")
        self.assertEqual(result["outcome"], "partial")
        self.assertFalse(s.run_finish(self.data, "synthetic-source", "run-02", "partial")["changed"])

    def test_source_run_without_start_fails(self):
        with self.assertRaises(s.IntakeError):
            s.run_finish(self.data, "synthetic-source", "no-start", "error")

    def test_conflicting_source_run_outcome_rejected(self):
        s.run_start(self.data, "synthetic-source", "run-03")
        s.run_finish(self.data, "synthetic-source", "run-03", "error")
        with self.assertRaises(s.IntakeError):
            s.run_finish(self.data, "synthetic-source", "run-03", "success")

    def test_stale_flag_self_heals_on_reingest(self):
        s.ingest(self.data, self.item())
        (self.data / "flag.json").write_text("{}")
        self.assertIn("flag.json:stale", s.status(self.data)["derived_warnings"])
        s.ingest(self.data, self.item())
        self.assertEqual(s.status(self.data)["derived_warnings"], [])

    def test_corrupt_state_can_be_rebuilt_from_log(self):
        s.ingest(self.data, self.item())
        (self.data / "state.json").write_text("{")
        self.assertIn("state.json:unreadable_or_corrupt", s.status(self.data)["derived_warnings"])
        (self.data / "state.json").unlink()
        self.assertEqual(s.rebuild(self.data)["status"], "rebuilt")
        self.assertEqual(s.status(self.data)["derived_warnings"], [])

    def test_corrupt_log_fails_closed(self):
        s.ingest(self.data, self.item())
        journal = next((self.data / "events").glob("*.jsonl"))
        with journal.open("ab") as out:
            out.write(b"{partial")
        with self.assertRaises(s.IntakeError):
            s.status(self.data)
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item("new"))

    def test_journal_event_seq_violation_fails(self):
        s.ingest(self.data, self.item())
        journal = next((self.data / "events").glob("*.jsonl"))
        record = json.loads(journal.read_text().splitlines()[0])
        record["seq"] = 9
        journal.write_text(json.dumps(record) + "\n")
        with self.assertRaises(s.IntakeError):
            s.status(self.data)

    def test_journal_duplicate_event_id_fails(self):
        s.ingest(self.data, self.item())
        journal = next((self.data / "events").glob("*.jsonl"))
        record = json.loads(journal.read_text().splitlines()[0])
        record["seq"] = 2
        with journal.open("a") as out:
            out.write(json.dumps(record) + "\n")
        with self.assertRaises(s.IntakeError):
            s.status(self.data)

    def test_journal_illegal_transition_fails(self):
        identifier = s.ingest(self.data, self.item())["item_id"]
        journal = next((self.data / "events").glob("*.jsonl"))
        with journal.open("a") as out:
            out.write(json.dumps({"schema_version": 1, "seq": 2,
                                  "event_id": "synthetic-bad-transition",
                                  "occurred_at": s.utc_now(), "kind": "item_transition",
                                  "item_id": identifier, "from_state": "unprocessed", "to_state": "reported"}) + "\n")
        with self.assertRaises(s.IntakeError):
            s.status(self.data)

    def test_unknown_event_kind_fails(self):
        s.ingest(self.data, self.item())
        journal = next((self.data / "events").glob("*.jsonl"))
        with journal.open("a") as out:
            out.write(json.dumps({"schema_version": 1, "seq": 2, "event_id": "unknown-kind-2",
                                  "occurred_at": s.utc_now(), "kind": "unknown"}) + "\n")
        with self.assertRaises(s.IntakeError):
            s.status(self.data)

    def test_derived_orphan_temporary_file_fails(self):
        (self.data / ".intake-temp-leftover").write_text("unfinished")
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item())

    def test_retention_preview_never_candidates_open(self):
        s.ingest(self.data, self.item())
        result = s.retention_preview(self.data, 0)
        self.assertEqual(result["eligible_count"], 0)
        self.assertFalse(result["deleted"])

    def test_retention_preview_terminal_only(self):
        a = s.ingest(self.data, self.item("one"))["item_id"]
        b = s.ingest(self.data, self.item("two"))["item_id"]
        s.transition(self.data, a, "discarded", "discard-a")
        s.transition(self.data, b, "audited", "audit-b")
        result = s.retention_preview(self.data, 0)
        self.assertEqual(result["eligible_item_ids"], [a])
        self.assertFalse(result["deleted"])

    def test_missing_data_directory_fails(self):
        with self.assertRaises(s.IntakeError):
            s.ensure_real_dir(self.root / "missing")

    def test_public_checkout_directory_rejected(self):
        with self.assertRaises(s.IntakeError):
            s.ensure_real_dir(ROOT)

    def test_events_symlink_rejected(self):
        target = self.root / "other"
        target.mkdir()
        try:
            (self.data / "events").symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink not available")
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item())

    def test_data_file_symlink_rejected(self):
        other = self.root / "outside.json"
        other.write_text("{}")
        try:
            (self.data / "flag.json").symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink not available")
        with self.assertRaises(s.IntakeError):
            s.ingest(self.data, self.item())

    def test_cli_accepted_and_duplicate(self):
        self.item_file.write_text(json.dumps(self.item()), encoding="utf-8")
        first = self.cli("ingest", "--file", str(self.item_file))
        second = self.cli("ingest", "--file", str(self.item_file))
        self.assertEqual((first.returncode, second.returncode), (0, 0))
        self.assertTrue(json.loads(first.stdout)["added"])
        self.assertFalse(json.loads(second.stdout)["added"])

    def test_cli_bad_input_returns_error_not_zero(self):
        self.item_file.write_text('{"where":{}}')
        bad = self.cli("ingest", "--file", str(self.item_file))
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(json.loads(bad.stdout)["status"], "error")
        self.assertNotIn(str(self.data), bad.stdout)

    @unittest.skipIf(sys.platform == "win32", "fcntl-only lock contention test")
    def test_lock_collision_returns_3(self):
        import fcntl
        with (self.data / ".intake.lock").open("w") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            clash = self.cli("status")
            self.assertEqual(clash.returncode, 3)
            self.assertEqual(json.loads(clash.stdout)["status"], "locked")


if __name__ == "__main__":
    unittest.main()
