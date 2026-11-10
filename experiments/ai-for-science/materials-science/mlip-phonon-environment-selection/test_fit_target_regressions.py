import importlib.util
from pathlib import Path

import numpy as np

MODULE_PATH = Path(__file__).with_name("fit_target_regressions.py")
SPEC = importlib.util.spec_from_file_location("fit_target_regressions", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def feature_row(candidate_id, target_id, starting_error):
    return {
        "candidate_id": candidate_id,
        "target_material_id": target_id,
        "source_family": candidate_id,
        "selection_rule": "rule",
        "target_descriptor": {
            "starting_frequency_mae_thz": starting_error,
            "starting_predicted_stability_margin_kelvin": 1.0,
            "element_count": 2,
            "unitcell_atoms": 4,
            "elements": ["Li", "O"],
        },
        "chemical_support": {
            "element_distribution_overlap": 0.8,
            "record_fraction_containing_all_target_elements": 0.5,
        },
        "nearest_neighbor_affinity": {
            "top_five_percent_element_set_jaccard": 0.9,
        },
    }


def test_grouped_logistic_predictions_cover_every_example():
    candidates = {
        f"e-{index}": {
            "signal_density_per_atom": float(index + 1),
            "effective_signal_coverage": 0.1 * (index + 1),
            "mean_target_affinity": 0.2 * (index + 1),
        }
        for index in range(4)
    }
    rows = [
        feature_row(candidate_id, f"mp-{target}", 0.1 + 0.1 * target)
        for candidate_id in candidates
        for target in range(3)
    ]
    labels = np.asarray([float(index % 2) for index in range(len(rows))])
    groups = [row["candidate_id"] for row in rows]
    probabilities, penalties = MODULE.grouped_predictions(
        rows,
        labels,
        candidates,
        ["log_starting_frequency_mae", "log_signal_density"],
        groups,
    )
    assert len(probabilities) == len(rows)
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))
    assert len(penalties) == 4
    report = MODULE.metrics(labels, probabilities)
    assert 0.0 <= report["brier_score"] <= 1.0


def test_candidate_identity_design_uses_one_column_per_training_candidate():
    candidates = {
        "a": {
            "signal_density_per_atom": 1.0,
            "effective_signal_coverage": 0.2,
            "mean_target_affinity": 0.3,
        },
        "b": {
            "signal_density_per_atom": 2.0,
            "effective_signal_coverage": 0.4,
            "mean_target_affinity": 0.5,
        },
    }
    rows = [feature_row("a", "mp-1", 0.2), feature_row("b", "mp-1", 0.2)]
    state = MODULE.design_state(rows, candidates, ["one_hot_candidate_id"])
    matrix = MODULE.design(rows, candidates, state)
    assert state["categories"]["candidate_id"] == ["a", "b"]
    assert matrix.shape == (2, 3)
