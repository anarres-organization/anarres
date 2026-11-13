from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ReleasedAntibodyPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gate = json.loads((ROOT / "RELEASE_GATE.json").read_text())
        cls.results = json.loads((ROOT / "RESULTS.json").read_text())
        cls.audit = json.loads((ROOT / "RESULT_AUDIT.json").read_text())
        cls.curves = json.loads((ROOT / "OUTCOME_CURVES.json").read_text())

    def test_release_gate_covers_complete_matrix(self) -> None:
        self.assertEqual(self.gate["status"], "RELEASE_GATE_PASSED__OUTCOMES_MAY_BE_OPENED")
        self.assertEqual(self.gate["unit_count"], 150)
        identities = {
            (record["assay"], record["strategy"], record["seed"]) for record in self.gate["records"]
        }
        self.assertEqual(len(identities), 150)

    def test_frozen_ucb_result_is_reported_without_selector_dominance(self) -> None:
        primary = self.results["primary_result"]
        self.assertAlmostEqual(primary["mean_pairwise_credit"], 5 / 6)
        self.assertAlmostEqual(primary["mean_normalized_regret"], 0.24052891228048612)
        self.assertAlmostEqual(primary["mean_best_strategy_credit"], 0.5)
        self.assertEqual(
            sum(row["selected_is_best_credit"] for row in self.results["assay_results"]),
            3,
        )
        self.assertLess(
            self.audit["strategy_metrics"]["greedy"]["mean_normalized_regret"],
            self.audit["strategy_metrics"]["ucb"]["mean_normalized_regret"],
        )

    def test_released_curves_cover_every_unit(self) -> None:
        self.assertEqual(self.curves["curve_count"], 150)
        self.assertTrue(all(len(row["recall_curve"]) == 10 for row in self.curves["curves"]))
        self.assertEqual(self.audit["frozen_ucb_contrasts"]["assays_where_ucb_exceeds_random"], 6)


if __name__ == "__main__":
    unittest.main()
