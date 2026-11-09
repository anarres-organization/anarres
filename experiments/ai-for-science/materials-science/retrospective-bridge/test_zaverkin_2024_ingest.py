import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "ingest_zaverkin_2024.py"
SPEC = importlib.util.spec_from_file_location("ingest_zaverkin_2024", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_reconstructs_matched_repeated_panels():
    payload = MODULE.reconstruct()
    assert payload["panel_count"] == 8
    assert payload["arm_count"] == 46
    assert payload["matched_contract"]["maximum_training_and_validation_configurations"] == 512
    assert all(
        arm["pre_outcome_measurements"]["training_configuration_count"] == 512
        for arm in payload["arms"]
    )
    assert {arm["outcome"]["independent_runs"] for arm in payload["arms"]} == {3, 5}


def test_exact_primary_table_values_are_preserved():
    payload = MODULE.reconstruct()
    lookup = {(arm["panel_id"], arm["environment"]): arm for arm in payload["arms"]}
    alanine = lookup[
        (
            f"{MODULE.SOURCE_ID}:alanine_1200K_test:energy_rmse",
            "uncertainty_1200K",
        )
    ]
    assert alanine["outcome"] == {
        "mean_rmse": 1.47,
        "sd_across_runs": 0.09,
        "independent_runs": 5,
    }
    mil53 = lookup[
        (
            f"{MODULE.SOURCE_ID}:mil53_generation_600K_600K_test:stress_rmse",
            "uncertainty_biased_0MPa",
        )
    ]
    assert mil53["outcome"]["mean_rmse"] == 36.60


def test_metadynamics_is_excluded_from_matched_panels():
    payload = MODULE.reconstruct()
    assert all("metadynamics" not in arm["environment"] for arm in payload["arms"])
