import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("summarize_development_outcomes.py")
SPEC = importlib.util.spec_from_file_location("summarize_development_outcomes", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_summary_uses_seed_mean_regression_and_equal_cost_utility(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "environments": {"development": [{"candidate_id": "environment"}]},
                "randomization": {"training_seeds": [0, 1]},
                "environment_budget": {"checkpoints_after_passes": [1]},
            }
        ),
        encoding="utf-8",
    )
    roles = tmp_path / "roles.json"
    roles.write_text(json.dumps({"roles": {"development": ["mp-1"]}}), encoding="utf-8")
    starting = tmp_path / "starting.json"
    starting.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "material_id": "mp-1",
                        "role": "development",
                        "frequency_mae_thz": 1.0,
                        "reference_stable": True,
                        "predicted_stable": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "results"
    for seed, error in ((0, 1.0), (1, 1.2)):
        output = root / "environment" / f"seed_{seed}" / "epoch_0001" / "mp-1.json"
        output.parent.mkdir(parents=True)
        output.write_text(
            json.dumps(
                {
                    "material_id": "mp-1",
                    "backend": "nequix",
                    "model_sha256": f"model-{seed}",
                    "metrics": {
                        "frequency_mae_thz": error,
                        "frequency_rmse_thz": error,
                        "reference_stability_margin_kelvin": 1.0,
                        "predicted_stability_margin_kelvin": 1.0,
                        "reference_stable": True,
                        "predicted_stable": True,
                    },
                }
            ),
            encoding="utf-8",
        )
    summary = MODULE.summarize(contract, roles, starting, root)
    assert summary["seed_mean_curves"][0]["utility_thz"] == pytest.approx(-0.1)
    assert summary["target_regressions"][0]["frequency_error_regression"] is True
    assert summary["counts"]["evaluation_records"] == 2
