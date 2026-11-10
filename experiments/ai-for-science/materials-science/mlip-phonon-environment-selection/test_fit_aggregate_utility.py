import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("fit_aggregate_utility.py")
SPEC = importlib.util.spec_from_file_location("fit_aggregate_utility", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_complete_environment_cross_validation_predicts_every_curve_point():
    candidates = {
        f"e-{index}": {
            "signal_density_per_atom": float(index + 1),
            "effective_signal_coverage": 0.1 * (index + 1),
            "mean_target_affinity": 0.2 * (index + 1),
        }
        for index in range(4)
    }
    rows = [
        {
            "candidate_id": candidate_id,
            "pass": epoch,
            "utility_thz": 0.1 * epoch + 0.05 * index,
        }
        for index, candidate_id in enumerate(candidates)
        for epoch in (1, 2)
    ]
    predictions, metrics = MODULE.cross_validate(rows, candidates, ["log_signal_density"], [1, 2])
    assert len(predictions) == 8
    assert metrics["decision_count"] == 2
    assert 0.0 <= metrics["pairwise_rank_accuracy"] <= 1.0


def test_allocation_baselines_score_all_prespecified_rules():
    candidates = {
        f"source-{index % 2}__{'hash_uniform' if index < 2 else 'coverage'}": {
            "signal_density_per_atom": float(index + 1),
            "effective_signal_coverage": 0.1 * (index + 1),
            "mean_target_affinity": 0.2 * (index + 1),
        }
        for index in range(4)
    }
    rows = [
        {"candidate_id": candidate_id, "pass": epoch, "utility_thz": 0.1 * index}
        for index, candidate_id in enumerate(candidates)
        for epoch in (1, 2)
    ]
    results = MODULE.allocation_baselines(rows, candidates, [1, 2])
    assert {row["name"] for row in results} == {
        "equal_weight_signal_coverage_affinity",
        "fixed_source_family_selected_inside_each_training_fold",
        "fixed_selection_rule_selected_inside_each_training_fold",
        "hash_uniform",
        "random_choice_expectation",
    }
