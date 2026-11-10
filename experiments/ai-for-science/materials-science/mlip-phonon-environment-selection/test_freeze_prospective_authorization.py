import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("freeze_prospective_authorization.py")
SPEC = importlib.util.spec_from_file_location("freeze_prospective_authorization", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_authorization_binds_forecasts_without_outcomes(tmp_path):
    contract = tmp_path / "contract.json"
    protocol = tmp_path / "protocol.json"
    aggregate = tmp_path / "aggregate.json"
    regressions = tmp_path / "regressions.json"
    write_json(contract, {"artifact": "contract"})
    write_json(protocol, {"artifact": "protocol"})
    write_json(
        aggregate,
        {
            "prospective_boundary": {
                "prospective_candidate_training_outcomes_used": False,
                "prospective_target_outcomes_used": False,
            },
            "selected_model": {"name": "joint"},
            "prospective_baseline_decisions": [
                {
                    "name": "random_choice_expectation",
                    "pass": 1,
                    "selected_candidates": ["a", "b", "c", "d"],
                }
            ],
            "prospective_forecast": [
                {
                    "candidate_id": candidate,
                    "curve": [
                        {"pass": epoch, "predicted_utility_thz": score + epoch}
                        for epoch in (1, 2, 3, 4)
                    ],
                }
                for candidate, score in (("a", 0.0), ("b", 1.0), ("c", 2.0), ("d", 3.0))
            ],
        },
    )
    write_json(
        regressions,
        {
            "prospective_boundary": {
                "prospective_candidate_training_outcomes_used": False,
                "prospective_target_outcomes_used": False,
            },
            "selected_model": {"name": "full"},
            "prospective_predictions": [{"probability": 0.2}] * 200,
        },
    )

    result = MODULE.freeze(contract, protocol, aggregate, regressions)

    assert result["status"] == "prospective_predictions_frozen"
    assert result["forecast_counts"] == {
        "environment_curves": 4,
        "environment_budget_points": 16,
        "target_regression_probabilities": 200,
    }
    assert [row["selected_candidate"] for row in result["decisions"]] == ["d"] * 4
    assert result["baseline_decisions"][0]["name"] == "random_choice_expectation"
    assert not any(result["outcome_boundary"].values())
