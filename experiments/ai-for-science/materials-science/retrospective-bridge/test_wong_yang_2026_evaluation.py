import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parent / "scripts" / "evaluate_wong_yang_2026.py"
SPEC = importlib.util.spec_from_file_location("evaluate_wong_yang_2026", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_summarize_predictions_uses_per_atom_energy_and_all_force_components():
    records = [
        {
            "atom_count": 2,
            "energy_error_meV_per_atom": 2.0,
            "force_error_eV_per_A": [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]],
        },
        {
            "atom_count": 1,
            "energy_error_meV_per_atom": -2.0,
            "force_error_eV_per_A": [[0.0, 2.0, 0.0]],
        },
    ]
    result = MODULE.summarize_predictions(records)
    assert result["structure_count"] == 2
    assert result["atom_count"] == 3
    assert result["energy_mae_meV_per_atom"] == 2.0
    assert result["energy_rmse_meV_per_atom"] == 2.0
    assert result["energy_bias_meV_per_atom"] == 0.0
    assert np.isclose(result["force_component_mae_eV_per_A"], 4 / 9)
    assert np.isclose(result["force_vector_mae_eV_per_A"], 4 / 3)


def test_budget_models_define_five_matched_pairs():
    assert sorted(MODULE.BUDGET_MODELS) == [10, 21, 31, 40, 50]
    assert all(len(paths) == 2 for paths in MODULE.BUDGET_MODELS.values())
