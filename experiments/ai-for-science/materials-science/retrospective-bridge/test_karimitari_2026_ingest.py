import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def payload() -> dict:
    return json.loads(
        (ROOT / "data" / "karimitari_2026_catalysis_environment_audit.json").read_text()
    )


def lookup() -> dict[tuple[str, str, str], dict]:
    return {
        (arm["training_regime"], arm["environment"], arm["endpoint"]): arm
        for arm in payload()["arms"]
    }


def test_exact_tables_yield_six_cost_sensitive_panels():
    data = payload()
    assert data["panel_count"] == 6
    assert data["arm_count"] == 25
    assert {panel["candidate_count"] for panel in data["panels"]} == {2, 3, 6}


def test_exact_scratch_and_fine_tuning_values_are_preserved():
    arms = lookup()
    assert arms[("from_scratch", "fs_bma", "reaction_energy_metal")]["outcome"] == {
        "mean_absolute_error_eV": 0.659
    }
    assert arms[("from_scratch", "fs_all", "activation_barrier_metal")]["outcome"] == {
        "mean_absolute_error_eV": 0.175
    }
    assert arms[("fine_tuning", "ft_bma", "reaction_energy_metal")]["outcome"] == {
        "mean_absolute_error_eV": 0.238
    }
    assert arms[("fine_tuning", "ft_all", "reaction_energy_metal_oxide")]["outcome"] == {
        "mean_absolute_error_eV": 0.277
    }


def test_model_start_changes_the_value_of_added_environment_components():
    arms = lookup()
    scratch_relax = arms[("from_scratch", "fs_bma", "reaction_energy_metal")]["outcome"][
        "mean_absolute_error_eV"
    ]
    scratch_all = arms[("from_scratch", "fs_all", "reaction_energy_metal")]["outcome"][
        "mean_absolute_error_eV"
    ]
    fine_tune_relax = arms[("fine_tuning", "ft_bma", "reaction_energy_metal")]["outcome"][
        "mean_absolute_error_eV"
    ]
    fine_tune_all = arms[("fine_tuning", "ft_all", "reaction_energy_metal")]["outcome"][
        "mean_absolute_error_eV"
    ]
    assert scratch_all < scratch_relax
    assert fine_tune_all > fine_tune_relax


def test_cost_and_training_regime_boundaries_are_explicit():
    lines = payload()["interpretation_boundary"]
    assert any("different configuration counts" in line for line in lines)
    assert any("initialization" in line and "OMAT replay" in line for line in lines)
    assert any("39,584" in line and "39,983" in line for line in lines)
