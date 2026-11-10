import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("freeze_development_modeling_protocol.py")
SPEC = importlib.util.spec_from_file_location("freeze_development_modeling_protocol", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_protocol_preserves_outcome_boundary(tmp_path):
    decision = tmp_path / "decision.json"
    decision.write_text(
        json.dumps(
            {
                "prospective_environment_selection": {"decision_baselines": ["random"]},
                "target_regression_prediction": {
                    "primary_endpoint": {"name": "regression"},
                    "secondary_endpoints": [],
                    "metrics": ["brier_score"],
                    "negative_controls": ["permuted"],
                },
                "outcome_boundary": {"candidate_training_outcomes_used": False},
            }
        ),
        encoding="utf-8",
    )
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps({"outcome_boundary": {"development_candidate_training_outcomes_used": False}}),
        encoding="utf-8",
    )
    starting = tmp_path / "starting.json"
    starting.write_text("{}", encoding="utf-8")
    features = tmp_path / "features.json"
    features.write_text(
        json.dumps({"outcome_boundary": {"development_candidate_training_outcomes_used": False}}),
        encoding="utf-8",
    )
    result = MODULE.freeze(decision, contract, starting, features)
    assert result["status"] == "frozen_before_development_outcome_analysis"
    assert not any(result["outcome_boundary"].values())
