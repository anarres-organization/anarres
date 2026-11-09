import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def payload() -> dict:
    return json.loads(
        (ROOT / "data" / "haenseroth_dressler_2026_trajectory_stride_panels.json").read_text()
    )


def test_all_released_stride_decisions_are_complete():
    data = payload()
    assert data["panel_count"] == 336
    assert data["arm_count"] == 672
    by_panel = defaultdict(list)
    for arm in data["arms"]:
        by_panel[arm["panel_id"]].append(arm)
    assert all(
        {arm["environment"] for arm in arms} == {"trajectory_stride_10", "trajectory_stride_100"}
        for arms in by_panel.values()
    )
    assert Counter(arm["training_mode"] for arm in data["arms"]) == {
        "finetune": 420,
        "train": 252,
    }


def test_exact_released_metrics_and_coverage_coordinates():
    data = payload()
    lookup = {
        (
            arm["training_mode"],
            arm["training_configuration_count"],
            arm["framework"],
            arm["material_system"],
            arm["endpoint"],
            arm["environment"],
        ): arm
        for arm in data["arms"]
    }
    cdp = lookup[
        (
            "finetune",
            2000,
            "mace",
            "cdp",
            "force_mae_eV_per_A",
            "trajectory_stride_100",
        )
    ]
    assert cdp["outcome"]["mean_absolute_error"] == 0.035499671152132234
    assert cdp["pre_outcome_measurements"]["trajectory_frame_span"] == 199901
    assert cdp["pre_outcome_measurements"]["relative_trajectory_span"] == 10.0


def test_broader_trajectory_span_is_helpful_but_not_universal():
    data = payload()
    winners = Counter()
    by_panel = defaultdict(list)
    for arm in data["arms"]:
        by_panel[arm["panel_id"]].append(arm)
    for arms in by_panel.values():
        winners[
            max(arms, key=lambda arm: arm["derived"]["panel_normalized_utility"])["environment"]
        ] += 1
    assert winners == {"trajectory_stride_100": 213, "trajectory_stride_10": 123}


def test_reference_trajectory_cost_and_seed_boundary_are_explicit():
    data = payload()
    assert any(
        "reference-trajectory generation cost" in line.lower()
        for line in data["interpretation_boundary"]
    )
    assert any("one trained model per arm" in line for line in data["interpretation_boundary"])
