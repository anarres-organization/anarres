#!/usr/bin/env python3
"""Checks for prospective Snowball decision and regression scoring."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "score_snowball_panel", HERE / "score_snowball_panel.py"
)
assert SPEC and SPEC.loader
SCORER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCORER)


def fixtures() -> tuple[dict, dict, dict]:
    contract = {
        "study_id": "snowball-test",
        "status": "FROZEN_BEFORE_CANDIDATE_OUTCOMES",
        "candidate_outcomes_opened": False,
        "candidate_ids": ["candidate_a", "candidate_b"],
        "target_ids": ["target_1", "target_2"],
        "target_weights": {"target_1": 0.5, "target_2": 0.5},
        "regression_margins": {"target_1": 0.05, "target_2": 0.05},
        "replicate_seeds": [1, 2, 3],
        "generated_token_budget_per_intervention": 1000,
        "generated_token_tolerance": 0,
        "uncertainty": {"resamples": 200, "random_seed": 7},
    }
    predictions = {
        "study_id": "snowball-test",
        "protected_outcomes_opened": False,
        "candidates": [
            {
                "candidate_id": "candidate_a",
                "abstain": False,
                "targets": {
                    "target_1": {
                        "change": 0.1,
                        "interval": [0.0, 0.2],
                        "regression_probability": 0.1,
                    },
                    "target_2": {
                        "change": 0.1,
                        "interval": [0.0, 0.2],
                        "regression_probability": 0.1,
                    },
                },
            },
            {
                "candidate_id": "candidate_b",
                "abstain": False,
                "targets": {
                    "target_1": {
                        "change": -0.1,
                        "interval": [-0.2, 0.0],
                        "regression_probability": 0.9,
                    },
                    "target_2": {
                        "change": 0.1,
                        "interval": [0.0, 0.2],
                        "regression_probability": 0.2,
                    },
                },
            },
        ],
    }
    outcomes = {
        "study_id": "snowball-test",
        "status": "COMPLETE_RELEASE_GATE_PASSED",
        "starting_policy_targets": {"target_1": 0.5, "target_2": 0.5},
        "cost": {
            "measurement_accelerator_hours": 2.0,
            "starting_evaluation_accelerator_hours": 1.0,
        },
        "candidates": [
            {
                "candidate_id": "candidate_a",
                "seeds": [
                    {
                        "seed": seed,
                        "generated_tokens": 1000,
                        "training_accelerator_hours": 10.0,
                        "evaluation_accelerator_hours": 1.0,
                        "targets": {"target_1": 0.6, "target_2": 0.55},
                    }
                    for seed in [1, 2, 3]
                ],
            },
            {
                "candidate_id": "candidate_b",
                "seeds": [
                    {
                        "seed": seed,
                        "generated_tokens": 1000,
                        "training_accelerator_hours": 10.0,
                        "evaluation_accelerator_hours": 1.0,
                        "targets": {"target_1": 0.3, "target_2": 0.6},
                    }
                    for seed in [1, 2, 3]
                ],
            },
        ],
    }
    return contract, predictions, outcomes


class SnowballPanelScoringTest(unittest.TestCase):
    def test_scores_decision_targets_and_regressions(self) -> None:
        contract, predictions, outcomes = fixtures()
        result = SCORER.score(contract, predictions, outcomes)
        self.assertEqual(result["selected_candidate"], "candidate_a")
        self.assertEqual(result["observed_best_candidates"], ["candidate_a"])
        self.assertAlmostEqual(result["allocation_regret"], 0.0)
        self.assertAlmostEqual(result["pairwise_ordering_accuracy"], 5 / 6)
        self.assertAlmostEqual(result["candidate_prediction_coverage"], 1.0)
        self.assertAlmostEqual(result["aggregate_utility_rmse"], (0.003125 / 2) ** 0.5)
        self.assertAlmostEqual(result["target_change_rmse"], (0.0125 / 4) ** 0.5)
        self.assertAlmostEqual(result["accepted_target_change_rmse"], result["target_change_rmse"])
        self.assertAlmostEqual(result["target_interval_coverage"], 1.0)
        self.assertEqual(result["regression"]["observed"], 1)
        self.assertAlmostEqual(result["regression"]["roc_auc"], 1.0)
        self.assertAlmostEqual(result["regression"]["average_precision"], 1.0)
        self.assertAlmostEqual(result["regression"]["recall_in_top_risk_20_percent"], 1.0)
        self.assertAlmostEqual(result["cost"]["total_accelerator_hours"], 69.0)
        self.assertIsNone(result["cost"]["utility_cost_conversion"])

    def test_retain_starting_policy_can_win(self) -> None:
        contract, predictions, outcomes = fixtures()
        for candidate in predictions["candidates"]:
            for target in candidate["targets"].values():
                target["change"] = -0.1
                target["interval"] = [-0.2, 0.0]
        result = SCORER.score(contract, predictions, outcomes)
        self.assertEqual(result["selected_candidate"], "retain_starting_policy")

    def test_incomplete_seed_matrix_is_rejected(self) -> None:
        contract, predictions, outcomes = fixtures()
        incomplete = copy.deepcopy(outcomes)
        incomplete["candidates"][0]["seeds"].pop()
        with self.assertRaisesRegex(ValueError, "frozen seeds"):
            SCORER.score(contract, predictions, incomplete)

    def test_unfrozen_contract_is_rejected(self) -> None:
        contract, predictions, outcomes = fixtures()
        contract["status"] = "DRAFT"
        with self.assertRaisesRegex(ValueError, "not frozen"):
            SCORER.score(contract, predictions, outcomes)

    def test_mismatched_compute_budget_is_rejected(self) -> None:
        contract, predictions, outcomes = fixtures()
        outcomes["candidates"][0]["seeds"][0]["generated_tokens"] = 999
        with self.assertRaisesRegex(ValueError, "generated-token budget differs"):
            SCORER.score(contract, predictions, outcomes)


if __name__ == "__main__":
    unittest.main()
