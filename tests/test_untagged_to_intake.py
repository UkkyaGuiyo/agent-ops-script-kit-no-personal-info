"""Synthetic watcher pending report to local intake mapping tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
from untagged_to_intake import convert  # noqa: E402
import shared_intake as intake  # noqa: E402
import tempfile


class WatcherAdapterTests(unittest.TestCase):
    def pending(self):
        return {"status": "pending", "delivery": "unconfirmed", "report": {
            "event_id": "synthetic-event-01", "when_utc": "2026-11-17T01:00:00+00:00",
            "count": 1, "items": [{"root": "fixture", "relative_path": "example.txt"}]}}

    def test_valid_mapping(self):
        item = convert(self.pending())
        self.assertEqual(item["where"]["source_id"], "untagged-watch")
        self.assertEqual(item["source_event_id"], "synthetic-event-01")
        self.assertEqual(item["payload"]["count"], 1)

    def test_converted_event_can_be_ingested_idempotently(self):
        with tempfile.TemporaryDirectory() as path:
            target = Path(path)
            item = convert(self.pending())
            accepted = intake.ingest(target, item)
            repeated = intake.ingest(target, item)
            self.assertTrue(accepted['added'])
            self.assertFalse(repeated['added'])
            self.assertEqual(accepted['item_id'], repeated['item_id'])
            self.assertEqual(intake.status(target)['flag']['unprocessed_count'], 1)

    def test_reject_nonpending(self):
        data = self.pending()
        data["status"] = "ok"
        with self.assertRaises(ValueError):
            convert(data)

    def test_mismatched_count_fails(self):
        data = self.pending()
        data["report"]["count"] = 2
        with self.assertRaises(ValueError):
            convert(data)

    def test_invalid_source_id_fails(self):
        with self.assertRaises(Exception):
            convert(self.pending(), "private path / hidden")


if __name__ == "__main__":
    unittest.main()
