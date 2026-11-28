#!/usr/bin/env python3
"""Checks for the public Snowball Micro210 SFT-to-RL pair audit."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class SnowballMicro210PairAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = json.loads((HERE / "SNOWBALL_MICRO210_PAIR_AUDIT.json").read_text())

    def test_summary_matches_pairs(self) -> None:
        changes = [row["rl_pass_at_1"] - row["sft_pass_at_1"] for row in self.audit["pairs"]]
        summary = self.audit["summary"]
        self.assertEqual(summary["interventions"], len(changes))
        self.assertAlmostEqual(summary["mean_pass_at_1_change"], sum(changes) / len(changes))
        self.assertEqual(summary["positive_changes"], sum(change > 0 for change in changes))
        self.assertEqual(summary["negative_changes"], sum(change < 0 for change in changes))

    def test_every_pair_uses_the_common_policy(self) -> None:
        self.assertEqual(self.audit["evaluation_contract"]["policy"], "Micro210 2026.11.23")
        self.assertTrue(all(row["sft_scored_attempts"] >= 422 for row in self.audit["pairs"]))
        self.assertTrue(all(row["rl_scored_attempts"] >= 422 for row in self.audit["pairs"]))

    def test_pairs_are_not_misrepresented_as_mixture_effects(self) -> None:
        self.assertEqual(self.audit["use"]["current_status"], "outcome pairs only")
        self.assertIn("not causal mixture effects", self.audit["boundary"])
        self.assertIn("Mochi results are excluded", self.audit["boundary"])


if __name__ == "__main__":
    unittest.main()
