from score_pbesol import auc, canonical_digest, concordance, evaluate, pairwise_order_accuracy


def test_auc_and_concordance_are_exact_for_perfect_order():
    assert auc([False, False, True, True], [0.0, 1.0, 2.0, 3.0]) == 1.0
    assert concordance([0.0, 1.0, 2.0], [0.0, 1.0, 2.0]) == 1.0


def test_pairwise_order_accuracy_gives_half_credit_for_ties():
    values = {"a": 2.0, "b": 2.0, "c": 1.0}
    assert pairwise_order_accuracy(["a", "b", "c"], values) == 5 / 6


def test_evaluate_uses_stable_threshold_and_composite_ranking():
    rows = [
        {
            "local_id": "a",
            "min_frequency": -0.2,
            "composite_score": 0.0,
            "threshold_probability_minus_0p1": 0.1,
            "prediction": -0.2,
        },
        {
            "local_id": "b",
            "min_frequency": 0.0,
            "composite_score": 2.0,
            "threshold_probability_minus_0p1": 0.9,
            "prediction": 0.0,
        },
    ]
    result = evaluate(rows, -0.1, 1)
    assert result["stable_records"] == 1
    assert result["top_k_stable_rate"] == 1.0
    assert result["roc_auc"] == 1.0
    assert result["minimum_frequency_mae_thz"] == 0.0


def test_canonical_digest_is_independent_of_key_order():
    assert canonical_digest({"a": 1, "b": 2}) == canonical_digest({"b": 2, "a": 1})
