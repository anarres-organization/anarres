"""Integrity tests for the public prospective SylloGym decision record."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reproduce_legal", ROOT / "scripts" / "reproduce.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProspectiveSylloGymTest(unittest.TestCase):
    """Check support, chronology, matched design, and derived conclusions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.outcomes = json.loads((ROOT / "data" / "outcomes.json").read_text())
        cls.freeze = json.loads((ROOT / "data" / "frozen-decision.json").read_text())
        cls.expected = json.loads((ROOT / "results" / "summary.json").read_text())

    def test_support_is_three_arms_by_three_seeds(self) -> None:
        records = self.outcomes["records"]
        self.assertEqual(len(records), 9)
        self.assertEqual({row["seed"] for row in records}, {42, 43, 44})
        self.assertEqual(len({row["arm"] for row in records}), 3)

    def test_evaluation_contract_is_common(self) -> None:
        contract = self.outcomes["contract"]
        self.assertEqual(contract["evaluation_task_generators"], 45)
        self.assertEqual(contract["evaluation_episodes_per_arm_seed"], 900)
        self.assertEqual(contract["independent_unit"], "paired_training_seed")

    def test_chronology_is_explicit(self) -> None:
        chronology = self.freeze["chronology"]
        self.assertFalse(chronology["candidate_outcomes_read_before_selector_freeze"])
        self.assertIn("after training launch", chronology["sesoi_and_interpretation"])

    def test_summary_reproduces(self) -> None:
        self.assertEqual(MODULE.compute(self.outcomes, self.freeze), self.expected)

    def test_result_is_abstention(self) -> None:
        self.assertEqual(self.expected["decision"], "abstain")
        self.assertEqual(self.expected["frozen_selection_regret_pp"], 0.0)
        for contrast in self.expected["contrasts"].values():
            self.assertLess(contrast["t95"][0], 0)
            self.assertGreater(contrast["t95"][1], 0)

    def test_guardrail_gate(self) -> None:
        self.assertTrue(self.expected["no_material_family_regression"])
        self.assertGreater(self.expected["minimum_family_guardrail_delta_pp"], -5.0)


if __name__ == "__main__":
    unittest.main()
