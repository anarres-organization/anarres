import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("summarize_starting_targets.py")
SPEC = importlib.util.spec_from_file_location("summarize_starting_targets", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_summary_preserves_roles_and_stability_margins(tmp_path):
    roles = tmp_path / "roles.json"
    roles.write_text(
        json.dumps(
            {
                "roles": {"development": ["mp-1"], "prospective": ["mp-2"]},
                "role_hashes": {"development": "d", "prospective": "p"},
            }
        ),
        encoding="utf-8",
    )
    results = tmp_path / "results"
    results.mkdir()
    for material_id in ("mp-1", "mp-2"):
        (results / f"{material_id}.json").write_text(
            json.dumps(
                {
                    "material_id": material_id,
                    "model_sha256": "m" * 64,
                    "backend": "nequix",
                    "workflow": {"distance_angstrom": 0.01},
                    "metrics": {
                        "frequency_mae_thz": 0.1,
                        "frequency_rmse_thz": 0.2,
                        "maximum_frequency_error_thz": 0.3,
                        "reference_stable": True,
                        "predicted_stable": True,
                        "reference_stability_margin_kelvin": 1.0,
                        "predicted_stability_margin_kelvin": 2.0,
                    },
                    "relaxation": {"converged": True},
                }
            ),
            encoding="utf-8",
        )
    summary = MODULE.summarize(roles, results, "m" * 64)
    assert summary["counts"] == {"development": 1, "prospective": 1}
    assert [row["role"] for row in summary["targets"]] == ["development", "prospective"]
    assert summary["outcome_boundary"]["candidate_training_outcomes_used"] is False
