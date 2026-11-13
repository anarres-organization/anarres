from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ReleasedProteinPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = json.loads((ROOT / "RELEASE_GATE.json").read_text())
        cls.results = json.loads((ROOT / "RESULTS.json").read_text())
        cls.audit = json.loads((ROOT / "RESULT_AUDIT.json").read_text())
        cls.curves = json.loads((ROOT / "OUTCOME_CURVES.json").read_text())

    def test_release_gate_covers_complete_matrix_and_memberships(self) -> None:
        self.assertEqual(self.gate["status"], "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED")
        self.assertEqual(self.gate["unit_count"], 175)
        self.assertEqual(len(self.gate["candidate_membership_sha256"]), 7)
        self.assertEqual(
            len(
                {
                    (record["dataset"], record["strategy"], record["seed"])
                    for record in self.gate["records"]
                }
            ),
            175,
        )

    def test_frozen_greedy_rule_has_low_regret(self) -> None:
        primary = self.results["primary_result"]
        self.assertAlmostEqual(primary["mean_pairwise_credit"], 0.8928571428571429)
        self.assertAlmostEqual(primary["mean_normalized_regret"], 0.05586555465277441)
        self.assertAlmostEqual(primary["mean_best_strategy_credit"], 4 / 7)
        metrics = self.audit["strategy_metrics"]
        self.assertLess(
            metrics["greedy"]["mean_normalized_regret"],
            metrics["ucb"]["mean_normalized_regret"],
        )
        self.assertLess(
            metrics["greedy"]["mean_normalized_regret"],
            metrics["random"]["mean_normalized_regret"],
        )

    def test_complete_curves_and_random_control_are_released(self) -> None:
        self.assertEqual(self.curves["curve_count"], 175)
        self.assertTrue(all(len(row["recall_curve"]) == 10 for row in self.curves["curves"]))
        self.assertEqual(
            self.audit["frozen_greedy_contrasts"]["datasets_where_greedy_exceeds_random"],
            7,
        )


if __name__ == "__main__":
    unittest.main()
