"""Integrity tests for the compact LAB learning-dynamics record."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("lab_reproduce", ROOT / "scripts" / "reproduce.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LabLearningDynamicsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.risk = json.loads((ROOT / "data" / "regression-risk.json").read_text())
        self.summary = MODULE.compute()

    def test_released_summary_is_reproduced(self) -> None:
        expected = json.loads((ROOT / "results" / "summary.json").read_text())
        self.assertEqual(self.summary, expected)

    def test_nested_support_is_explicit(self) -> None:
        support = self.risk["support"]
        self.assertEqual(support["trained_interventions"], 1)
        self.assertEqual(support["independent_generalization_unit"], "practice_area")
        self.assertEqual(support["practice_areas"], 34)

    def test_curve_extrema(self) -> None:
        self.assertEqual(self.summary["checkpoint_count"], 15)
        self.assertEqual(self.summary["best_step"], 40)
        self.assertEqual(self.summary["final_step"], 70)
        self.assertGreater(
            self.summary["best_criterion_pass_percent"],
            self.summary["final_criterion_pass_percent"],
        )

    def test_negative_controls(self) -> None:
        self.assertTrue(self.summary["static_beats_random_ap"])
        self.assertTrue(self.summary["static_beats_shuffled_ap"])

    def test_claim_boundary(self) -> None:
        boundary = " ".join(self.risk["claim_boundary"]).lower()
        self.assertIn("not causal", boundary)
        self.assertIn("not calibrated", boundary)


if __name__ == "__main__":
    unittest.main()
