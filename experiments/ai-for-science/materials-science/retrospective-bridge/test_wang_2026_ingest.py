import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_wang_2026", ROOT / "scripts" / "ingest_wang_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "wang_2026_entropy_panels.json").read_text())


def test_exact_table_bridge_is_complete_and_matched():
    data = payload()
    assert data["panel_count"] == 45
    assert data["arm_count"] == 90
    panels = {}
    for arm in data["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
        assert arm["outcome"]["independent_training_draws"] == 3
    assert len(panels) == 45
    assert {len(arms) for arms in panels.values()} == {2}
    assert all(
        {arm["environment"] for arm in arms} == {"entropy_driven", "random_md"}
        for arms in panels.values()
    )


def test_reproduces_reported_endpoint_and_independent_reversal():
    data = payload()
    by_panel = {arm["panel_id"] + ":" + arm["environment"]: arm for arm in data["arms"]}
    carbon_energy = by_panel[
        "wang_2026_dataset_aware_entropy:carbon:in_distribution:n800:energy_mae:entropy_driven"
    ]
    assert carbon_energy["outcome"]["mean_mae"] == 4.2
    carbon_ind_force_entropy = by_panel[
        "wang_2026_dataset_aware_entropy:carbon:independent_test:n800:force_mae:entropy_driven"
    ]
    carbon_ind_force_random = by_panel[
        "wang_2026_dataset_aware_entropy:carbon:independent_test:n800:force_mae:random_md"
    ]
    assert carbon_ind_force_entropy["outcome"]["mean_mae"] == 61.9
    assert carbon_ind_force_random["outcome"]["mean_mae"] == 40.5
    assert carbon_ind_force_random["derived"]["panel_normalized_utility"] == 1.0


def test_test_distribution_match_is_defined_before_outcomes():
    data = payload()
    for arm in data["arms"]:
        expected = (
            arm["environment"] == "entropy_driven"
            if arm["evaluation_distribution"] == "in_distribution"
            else arm["environment"] == "random_md"
        )
        assert arm["pre_outcome_measurements"]["target_distribution_match"] == int(expected)
