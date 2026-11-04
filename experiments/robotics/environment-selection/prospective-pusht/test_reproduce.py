"""Integrity tests for the public prospective PushT decision record."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reproduce_pusht", ROOT / "scripts" / "reproduce.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProspectivePushTTest(unittest.TestCase):
    """Check support, chronology, matched budgets, and derived results."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads((ROOT / "data" / "outcomes.json").read_text())
        cls.expected = json.loads((ROOT / "results" / "summary.json").read_text())

    def test_support_is_three_arms_by_three_seeds(self) -> None:
        records = self.data["records"]
        self.assertEqual(len(records), 9)
        self.assertEqual({row["seed"] for row in records}, {0, 1, 2})
        self.assertEqual(len({row["arm"] for row in records}), 3)

    def test_contract_is_matched(self) -> None:
        contract = self.data["contract"]
        self.assertEqual(contract["episodes_per_arm"], 52)
        self.assertEqual(contract["training_steps"], 175000)
        self.assertEqual(contract["evaluation_episodes_per_arm_seed"], 500)
        self.assertEqual(contract["independent_unit"], "paired_training_seed")

    def test_decision_was_frozen_before_outcomes(self) -> None:
        chronology = self.data["chronology"]
        self.assertTrue(chronology["decision_frozen_before_outcomes"])
        self.assertEqual(len(chronology["frozen_candidate_set"]), 2)

    def test_summary_reproduces(self) -> None:
        self.assertEqual(MODULE.compute(self.data), self.expected)

    def test_claim_is_abstention_not_superiority(self) -> None:
        self.assertTrue(self.expected["abstention_correct"])
        interval = self.expected["contrasts"]["calibra_minus_diversity"]["t95"]
        self.assertLess(interval[0], 0)
        self.assertGreater(interval[1], 0)


if __name__ == "__main__":
    unittest.main()
