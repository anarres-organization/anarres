import json
from pathlib import Path


PATH = Path(__file__).parent / "data" / "qi_2024_direct_panels.json"


def load():
    return json.loads(PATH.read_text())


def test_support_and_archive_identity():
    data = load()
    assert data["panel_count"] == 6
    assert data["arm_count"] == 12
    assert data["source_archive"]["bytes"] == 1_293_261_530
    assert data["source_archive"]["md5"] == "5316a79c9570d3cb5a7e25ae5ac101e0"


def test_training_budgets_are_nearly_matched():
    contract = load()["matched_contract"]
    direct = contract["direct_sampling_configurations"]
    manual = contract["manual_sampling_configurations"]
    assert abs(direct - manual) / max(direct, manual) < 0.002


def test_target_matched_environment_wins_every_panel():
    panels = {}
    for arm in load()["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
    assert len(panels) == 6
    for arms in panels.values():
        winner = max(arms, key=lambda arm: arm["derived"]["native_utility"])
        assert winner["pre_outcome_measurements"]["target_distribution_match"] == 1


def test_direct_has_broader_measured_coverage():
    contract = load()["matched_contract"]
    assert contract["direct_coverage_score"] == 0.996
    assert contract["manual_sampling_coverage_score"] == 0.642
