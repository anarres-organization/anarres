#!/usr/bin/env python3
"""Checks for the Grug mixture scale-transfer stress test."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "score_grug_scale_transfer", HERE / "score_grug_scale_transfer.py"
)
assert SPEC and SPEC.loader
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


class GrugScaleTransferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads((HERE / "GRUG_SCALE_TRANSFER_RESULTS.json").read_text())

    def test_result_reproduces(self) -> None:
        self.assertEqual(self.result, SCORER.build())

    def test_complete_native_target_surface(self) -> None:
        self.assertEqual(set(self.result["results"]), {"d768", "d1024", "d1536"})
        self.assertTrue(all(row["subsets"] == 16 for row in self.result["results"].values()))

    def test_schedule_difference_blocks_scaling_claim(self) -> None:
        self.assertIn("not an identical-contract", self.result["boundary"])
        self.assertIn("does not establish", self.result["interpretation"])


if __name__ == "__main__":
    unittest.main()
