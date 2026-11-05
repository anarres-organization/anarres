"""Integrity tests for the robotics external checks."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "external_reproduce", ROOT / "scripts" / "reproduce.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExternalChecksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guild = json.loads((ROOT / "data" / "guild.json").read_text())
        cls.sole = json.loads((ROOT / "data" / "sole-r1.json").read_text())

    def test_guild_score(self) -> None:
        score = MODULE.guild_score(self.guild)
        self.assertEqual(score["top_choice_correct"], 3)
        self.assertEqual(score["pairwise_correct"], 11)
        self.assertEqual(score["mean_allocation_regret_pp"], 1.25)
        self.assertEqual(score["advantage_over_semantic_only_pp"], 23.75)

    def test_released_summary_is_reproduced(self) -> None:
        expected = json.loads((ROOT / "results" / "summary.json").read_text())
        observed = {
            "guild": MODULE.guild_score(self.guild),
            "sole_r1": MODULE.sole_score(self.sole),
        }
        self.assertEqual(observed, expected)

    def test_guild_miss_is_retained(self) -> None:
        task = next(row for row in self.guild["tasks"] if row["task"] == "pink-cup-sink")
        self.assertEqual(task["guild_policy_responsive"], 50)
        self.assertEqual(task["expert_2"], 55)

    def test_sole_falsification_is_not_rewritten(self) -> None:
        score = MODULE.sole_score(self.sole)
        self.assertFalse(score["top_choice_correct"])
        self.assertTrue(score["false_completion_control_correct"])
        self.assertFalse(score["outcomes_read_for_selection"])

    def test_claim_boundaries(self) -> None:
        boundary = " ".join(self.sole["claim_boundary"]).lower()
        self.assertIn("not chronologically prospective", boundary)
        self.assertIn("one real-world training seed", boundary)


if __name__ == "__main__":
    unittest.main()
