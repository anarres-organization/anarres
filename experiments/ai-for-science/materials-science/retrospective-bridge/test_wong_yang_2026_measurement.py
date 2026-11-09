import importlib.util
import sys
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parent / "scripts" / "measure_wong_yang_2026.py"
SPEC = importlib.util.spec_from_file_location("measure_wong_yang_2026", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_effective_coverage_has_expected_limits():
    assert MODULE.effective_coverage(np.zeros(4)) == 0
    assert MODULE.effective_coverage(np.ones(4)) == 1
    assert np.isclose(MODULE.effective_coverage(np.asarray([1, 0, 0, 0])), 0.25)


def test_dataset_contract_has_five_matched_budgets():
    assert sorted(MODULE.DATASETS) == [10, 21, 31, 40, 50]
    assert all(len(paths) == 2 for paths in MODULE.DATASETS.values())


def test_summary_preserves_energy_measurements_when_force_labels_are_missing():
    rows = [
        {
            "atom_count": 2,
            "energy_error_meV_per_atom": 2.0,
            "force_error_mass_eV_per_A": 1.0,
            "force_error_norms_eV_per_A": [0.25, 0.75],
        },
        {
            "atom_count": 2,
            "energy_error_meV_per_atom": -1.0,
            "force_error_mass_eV_per_A": None,
            "force_error_norms_eV_per_A": None,
        },
    ]
    summary = MODULE.summarize(rows)
    assert summary["configuration_count"] == 2
    assert summary["force_labeled_configuration_count"] == 1
    assert summary["starting_energy_mae_meV_per_atom"] == 1.5
    assert summary["starting_force_error_density_eV_per_A_per_atom"] == 0.5
