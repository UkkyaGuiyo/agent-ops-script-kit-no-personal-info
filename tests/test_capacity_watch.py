"""Synthetic unit tests. No personal data, network, or external accounts."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from capacity_watch import WatchError, run  # noqa: E402


class CapacityWatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.target = self.folder / "synthetic-target"
        self.target.mkdir()

    def config(self, **overrides):
        entry = {"name": "sample", "path": "synthetic-target", "warning_bytes": 5}
        entry.update(overrides)
        file = self.folder / "settings.json"
        file.write_text(json.dumps({"targets": [entry]}), encoding="utf-8")
        return file

    def test_empty_directory_is_valid(self):
        self.assertEqual(run(self.config())["targets"][0]["bytes"], 0)

    def test_recursive_totals_and_threshold_boundary(self):
        (self.target / "one").write_bytes(b"abc")
        nested = self.target / "nested"
        nested.mkdir()
        (nested / "two").write_bytes(b"de")
        record = run(self.config())["targets"][0]
        self.assertEqual((record["bytes"], record["files"], record["warning"]), (5, 2, True))

    def test_relative_paths_are_config_relative(self):
        (self.target / "one").write_bytes(b"x")
        previous = Path.cwd()
        try:
            os.chdir(ROOT)
            self.assertEqual(run(self.config())["targets"][0]["bytes"], 1)
        finally:
            os.chdir(previous)

    def test_directory_symlink_is_skipped(self):
        outside = self.folder / "other"
        outside.mkdir()
        (outside / "data").write_bytes(b"private sample")
        try:
            (self.target / "alias").symlink_to(outside, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("Symlinks unavailable")
        record = run(self.config())["targets"][0]
        self.assertEqual(record["bytes"], 0)
        self.assertEqual(record["skipped_symlinks"], 1)

    def test_target_symlink_is_rejected(self):
        alias = self.folder / "alias"
        try:
            alias.symlink_to(self.target, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(WatchError):
            run(self.config(path="alias"))

    def test_ancestor_symlink_is_rejected(self):
        (self.target / "child").mkdir()
        alias = self.folder / "alias"
        try:
            alias.symlink_to(self.target, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(WatchError):
            run(self.config(path=str(alias / "child")))

    def test_missing_directory_fails_not_zero(self):
        with self.assertRaises(WatchError):
            run(self.config(path="missing"))

    def test_boolean_threshold_rejected(self):
        with self.assertRaises(WatchError):
            run(self.config(warning_bytes=True))

    def test_duplicate_name_rejected(self):
        config = self.config()
        raw = json.loads(config.read_text(encoding="utf-8"))
        raw["targets"].append(raw["targets"][0].copy())
        config.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaises(WatchError):
            run(config)

    def test_empty_target_list_rejected(self):
        config = self.config()
        config.write_text('{"targets": []}', encoding="utf-8")
        with self.assertRaises(WatchError):
            run(config)

    def test_cli_failure_redacts_private_path(self):
        config = self.config(path="missing")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "capacity_watch.py"),
             "--config", str(config)],
            text=True, capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "error")
        self.assertNotIn(str(self.folder), result.stdout)


if __name__ == "__main__":
    unittest.main()
