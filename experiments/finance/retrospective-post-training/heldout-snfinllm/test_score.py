#!/usr/bin/env python3
"""Tests for the scored SNFinLLM source holdout."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class HoldoutScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(HERE / "score_holdout.py")], check=True)
        cls.score = json.loads((HERE / "SCORE.json").read_text())

    def test_all_comparable_targets_are_scored(self) -> None:
        metrics = self.score["metrics"]["practical_rule"]
        self.assertEqual(metrics["panels"], 7)
        self.assertEqual(metrics["pairwise_comparisons"], 17)

    def test_observed_stage_directions(self) -> None:
        stages = self.score["adjacent_stage_audit"]
        self.assertEqual(stages["continued_pretraining_over_base"]["later_stage_wins"], 2)
        self.assertEqual(stages["sft_over_continued_pretraining"]["later_stage_losses"], 2)
        self.assertEqual(stages["dpo_over_sft"]["later_stage_wins"], 1)
        self.assertEqual(stages["dpo_over_sft"]["later_stage_losses"], 6)

    def test_frozen_ranking_result(self) -> None:
        metrics = self.score["metrics"]["practical_rule"]
        self.assertAlmostEqual(metrics["pairwise_ordering_credit"], 7 / 17)
        self.assertAlmostEqual(metrics["top_choice_credit"], 1 / 7)


if __name__ == "__main__":
    unittest.main()
