#!/usr/bin/env python3
"""Tests for the numerical-faithfulness source holdout."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class NumericalFaithfulnessHoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
        cls.score = json.loads((HERE / "SCORE.json").read_text())

    def test_freeze_precedes_score(self) -> None:
        self.assertEqual(self.score["freeze_commit"], "50c6583")
        self.assertEqual(self.score["status"], "SCORED_AFTER_FREEZE")

    def test_failed_direction_is_preserved(self) -> None:
        self.assertFalse(self.score["primary_prediction_correct"])
        self.assertEqual(self.score["directional_accuracy"], 0.0)
        self.assertEqual(self.score["directional_comparisons"], 4)

    def test_missing_coordinate_is_named(self) -> None:
        self.assertIn("grounding", self.score["diagnosis"]["missing_coordinate"])


if __name__ == "__main__":
    unittest.main()
