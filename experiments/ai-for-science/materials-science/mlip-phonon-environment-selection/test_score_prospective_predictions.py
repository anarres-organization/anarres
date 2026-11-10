import hashlib
import importlib.util
import json
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("score_prospective_predictions.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("score_prospective_predictions", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_score_matches_frozen_curves_and_target_probabilities(tmp_path):
    aggregate_path = tmp_path / "aggregate.json"
    regression_path = tmp_path / "regression.json"
    outcomes_path = tmp_path / "outcomes.json"
    authorization_path = tmp_path / "authorization.json"
    aggregate = {
        "prospective_forecast": [
            {
                "candidate_id": candidate,
                "curve": [
                    {
                        "pass": 1,
                        "predicted_utility_thz": prediction,
                        "empirical_half_width_thz": 0.2,
                    }
                ],
            }
            for candidate, prediction in (("a__rule", 0.1), ("b__rule", 0.2))
        ]
    }
    regressions = {
        "prospective_predictions": [
            {
                "candidate_id": candidate,
                "target_material_id": target,
                "frequency_error_regression_probability": probability,
            }
            for candidate, target, probability in (
                ("a__rule", "mp-1", 0.1),
                ("a__rule", "mp-2", 0.8),
                ("b__rule", "mp-1", 0.2),
                ("b__rule", "mp-2", 0.9),
            )
        ]
    }
    outcomes = {
        "prospective_boundary": {
            "prospective_candidate_training_outcomes_used": True,
            "prospective_target_outcomes_used": True,
        },
        "counts": {"evaluation_records": 8},
        "seed_mean_curves": [
            {"candidate_id": "a__rule", "pass": 1, "utility_thz": 0.0},
            {"candidate_id": "b__rule", "pass": 1, "utility_thz": 0.3},
        ],
        "target_regressions": [
            {
                "candidate_id": candidate,
                "target_material_id": target,
                "frequency_error_regression": label,
                "stability_regression": False,
                "validity_regression": False,
            }
            for candidate, target, label in (
                ("a__rule", "mp-1", False),
                ("a__rule", "mp-2", True),
                ("b__rule", "mp-1", False),
                ("b__rule", "mp-2", True),
            )
        ],
    }
    write(aggregate_path, aggregate)
    write(regression_path, regressions)
    write(outcomes_path, outcomes)
    write(
        authorization_path,
        {
            "aggregate_utility_fit_sha256": digest(aggregate_path),
            "target_regression_fit_sha256": digest(regression_path),
            "baseline_decisions": [
                {
                    "name": "random_choice_expectation",
                    "pass": 1,
                    "selected_candidates": ["a__rule", "b__rule"],
                }
            ],
        },
    )
    result = MODULE.score(authorization_path, aggregate_path, regression_path, outcomes_path)
    assert result["status"] == "prospective_test_scored"
    assert result["aggregate_utility"]["covered_points"] == 2
    assert result["target_regressions"]["roc_auc"] == 1.0
