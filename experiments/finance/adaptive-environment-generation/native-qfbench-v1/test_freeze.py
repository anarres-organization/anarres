"""Integrity checks for the frozen QF-Bench native-loop design."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class NativeQFBenchFreezeTest(unittest.TestCase):
    def test_partitions_are_disjoint(self) -> None:
        split = json.loads((ROOT / "TASK_SPLIT.json").read_text())
        groups = [split["shared_protected"]]
        for round_specification in split["rounds"]:
            groups.extend([round_specification["development"], round_specification["target"]])
        task_ids = [row["task_id"] for group in groups for row in group]
        self.assertEqual(len(task_ids), 10)
        self.assertEqual(len(task_ids), len(set(task_ids)))

    def test_every_task_is_content_addressed(self) -> None:
        split = json.loads((ROOT / "TASK_SPLIT.json").read_text())
        rows = list(split["shared_protected"])
        for round_specification in split["rounds"]:
            rows.extend(round_specification["development"])
            rows.extend(round_specification["target"])
        for row in rows:
            self.assertEqual(len(row["task_toml_sha256"]), 64)
            self.assertEqual(len(row["instruction_sha256"]), 64)

    def test_freeze_manifest(self) -> None:
        manifest = json.loads((ROOT / "FREEZE_MANIFEST.sha256.json").read_text())
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
