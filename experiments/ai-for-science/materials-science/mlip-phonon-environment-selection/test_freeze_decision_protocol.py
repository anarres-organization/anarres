from pathlib import Path

from freeze_decision_protocol import build_protocol


HERE = Path(__file__).resolve().parent


def test_protocol_freezes_selection_and_regression_without_outcomes():
    protocol = build_protocol(
        HERE / "FINAL_COST_MATCHED_PANEL.json", HERE / "TARGET_ROLES.json"
    )

    assert protocol["status"] == "frozen_before_candidate_training_outcomes"
    assert protocol["outcome_boundary"] == {
        "candidate_training_outcomes_used": False,
        "development_target_outcomes_used": False,
        "prospective_target_outcomes_used": False,
    }

    ranking = protocol["literature_derived_baseline"]["ranking"]
    assert len(ranking) == 16
    assert sorted(item["rank"] for item in ranking) == list(range(1, 17))
    assert sum(item["role"] == "development" for item in ranking) == 12
    assert sum(item["role"] == "prospective" for item in ranking) == 4

    for item in ranking:
        assert set(item) == {
            "candidate_id",
            "role",
            "score",
            "coordinates",
            "standardized_coordinates",
            "rank",
        }


def test_protocol_is_deterministic():
    first = build_protocol(
        HERE / "FINAL_COST_MATCHED_PANEL.json", HERE / "TARGET_ROLES.json"
    )
    second = build_protocol(
        HERE / "FINAL_COST_MATCHED_PANEL.json", HERE / "TARGET_ROLES.json"
    )
    assert first == second
