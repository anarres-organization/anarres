from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProspectiveMolecularReleaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freeze = load("PROSPECTIVE_FREEZE_V1.json")
        cls.training_gate = load("PROSPECTIVE_TRAINING_GATE.json")
        cls.endpoint_gate = load("PROSPECTIVE_ENDPOINT_GATE.json")
        cls.results = load("PROSPECTIVE_RESULTS.json")

    def test_release_artifacts_preserve_frozen_hashes(self) -> None:
        expected = {
            "PROSPECTIVE_FREEZE_V1.json": (
                "104e38c41b03d4b01e3fa7c09bde46ccab01abca1607377cfa89866facb32c5c"
            ),
            "PROSPECTIVE_TRAINING_GATE.json": (
                "036f2370b61ebc8534ac06b9330dc694d0ada2bfc6ba7706a66e10ee8c5a5433"
            ),
            "PROSPECTIVE_ENDPOINT_GATE.json": (
                "7150fcc5fba95e215e74f0e822a9d83b7a61bfcafbc7db1c6df6c50fc99e8b30"
            ),
            "PROSPECTIVE_RESULTS.json": (
                "c227acda48ab6b7e208055936a1d60ab2cee3fd7a09a43e98a46f7b4da79ec8f"
            ),
        }
        for name, digest in expected.items():
            self.assertEqual(sha256(ROOT / name), digest, name)

    def test_frozen_scorer_matches_forecast_receipt(self) -> None:
        scorer = ROOT / "scripts" / "score_prospective_results_frozen_v1.py"
        self.assertEqual(
            sha256(scorer),
            self.freeze["inputs"]["scoring_implementation_sha256"],
        )
        self.assertEqual(
            sha256(ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"),
            self.freeze["inputs"]["contract_sha256"],
        )

    def test_chronology_gates_preserve_unopened_state(self) -> None:
        self.assertFalse(self.freeze["prospective_outcomes_opened"])
        self.assertFalse(self.training_gate["endpoint_outcomes_opened"])
        self.assertEqual(self.training_gate["run_count"], 4)
        self.assertEqual(self.training_gate["checkpoint_count"], 12)
        self.assertTrue(self.endpoint_gate["comparative_scoring_authorized"])
        self.assertEqual(self.endpoint_gate["panel_count"], 14)

    def test_results_are_bound_to_freeze_and_complete_gate(self) -> None:
        self.assertEqual(
            self.results["inputs"]["forecast_freeze_sha256"],
            sha256(ROOT / "PROSPECTIVE_FREEZE_V1.json"),
        )
        self.assertEqual(
            self.results["inputs"]["endpoint_gate_sha256"],
            sha256(ROOT / "PROSPECTIVE_ENDPOINT_GATE.json"),
        )
        self.assertTrue(self.results["prospective_outcomes_opened"])
        self.assertEqual(len(self.results["seed_records"]), 12)

    def test_point_forecast_is_correct_but_rule_abstains(self) -> None:
        decisions = self.results["decisions"]
        self.assertEqual(len(decisions), 3)
        self.assertTrue(all(row["point_prediction_correct"] for row in decisions))
        self.assertTrue(all(row["point_prediction_regret"] == 0 for row in decisions))
        self.assertTrue(all(row["abstain"] for row in decisions))
        self.assertTrue(all(not row["decision_issued"] for row in decisions))
        self.assertEqual(sum(row["seed_winner_agreement"] for row in decisions), 2)
        self.assertIsNone(self.results["issued_decision_mean_regret"])

    def test_graph_aware_forecast_gets_pair_order(self) -> None:
        graph = self.results["model_scores"]["graph_aware"]
        operational = self.results["model_scores"]["operational"]
        self.assertEqual(graph["pairwise_ordering"], 1.0)
        self.assertEqual(operational["pairwise_ordering"], 0.0)
        self.assertLess(operational["curve_rmse"], graph["curve_rmse"])


if __name__ == "__main__":
    unittest.main()
