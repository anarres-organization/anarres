#!/usr/bin/env python3
"""Tests for the strict task-level finance transfer audit."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "score.py"
SCORE = HERE / "SCORE.json"


class StrictTaskLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], check=True)
        cls.result = json.loads(SCORE.read_text())

    def test_support(self) -> None:
        self.assertEqual(self.result["support"]["sources"], 7)
        self.assertEqual(self.result["support"]["panels"], 79)
        self.assertEqual(self.result["support"]["arms"], 241)

    def test_fixed_rule_beats_more_data(self) -> None:
        result = self.result["evaluations"]["leave_one_source_out"]
        practical = result["practical_rule"]
        more_data = result["more_data"]
        self.assertGreater(practical["pairwise_ordering"], more_data["pairwise_ordering"])
        self.assertLess(practical["mean_normalized_regret"], more_data["mean_normalized_regret"])

    def test_source_comparison_has_no_losses(self) -> None:
        paired = self.result["paired_source_comparison"]
        self.assertEqual(paired["study_wins"], 6)
        self.assertEqual(paired["study_losses"], 0)
        self.assertEqual(paired["study_ties"], 1)


if __name__ == "__main__":
    unittest.main()
