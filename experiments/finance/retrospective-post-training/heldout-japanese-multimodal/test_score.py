#!/usr/bin/env python3
"""Tests for the Japanese finance source holdout."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class JapaneseFinanceHoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
        cls.score = json.loads((HERE / "SCORE.json").read_text())

    def test_task_level_score(self) -> None:
        self.assertEqual(self.score["task_level_correct"], 4)
        self.assertEqual(self.score["task_level_total"], 8)
        self.assertEqual(self.score["task_level_directional_accuracy"], 0.5)

    def test_visual_claim_is_unscored(self) -> None:
        comparison = self.score["frozen_comparisons"]["visual_adaptation_over_text_only"]
        self.assertEqual(comparison["status"], "UNSCORABLE")

    def test_broad_path_claim_fails(self) -> None:
        comparison = self.score["frozen_comparisons"]["full_path_over_skip_stage"]
        self.assertEqual(comparison["correct_targets"], 1)
        self.assertEqual(comparison["targets"], 3)


if __name__ == "__main__":
    unittest.main()
