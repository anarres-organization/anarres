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


def test_prospective_baseline_decisions_are_frozen_without_outcomes():
    rows = [
        {"candidate_id": "source-a__coverage", "pass": 1, "utility_thz": 0.2},
        {"candidate_id": "source-b__target_affinity", "pass": 1, "utility_thz": 0.1},
    ]
    ranking = [
        {"candidate_id": "source-a__coverage", "rank": 1},
        {"candidate_id": "source-b__target_affinity", "rank": 2},
        {"candidate_id": "source-a__low_signal", "rank": 3},
    ]
    result = MODULE.freeze_prospective_baselines(
        rows,
        ["source-b__target_affinity", "source-a__low_signal"],
        [1],
        ranking,
    )
    equal_weight = next(
        row for row in result if row["name"] == "equal_weight_signal_coverage_affinity"
    )
    hash_uniform = next(row for row in result if row["name"] == "hash_uniform")
    assert equal_weight["selected_candidates"] == ["source-b__target_affinity"]
    assert hash_uniform["applicable"] is False
