import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_kim_2026", ROOT / "scripts" / "ingest_kim_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "kim_2026_density_diversity_panels.json").read_text())


def test_five_seed_panels_are_complete_and_cost_matched():
    data = payload()
    assert data["panel_count"] == 12
    assert data["arm_count"] == 36
    panels = {}
    for arm in data["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
        assert arm["pre_outcome_measurements"]["training_configuration_count"] == 512
        assert arm["outcome"]["independent_training_seeds"] == 5
        assert len(arm["outcome"]["seed_scores"]) == 5
    assert {len(arms) for arms in panels.values()} == {3}
    assert all(
        {arm["environment"] for arm in arms}
        == {"no_variance", "temperature_diverse", "density_diverse"}
        for arms in panels.values()
    )


def test_reproduces_density_diversity_ordering_and_high_density_reversal():
    data = payload()
    by_panel = {}
    for arm in data["arms"]:
        by_panel.setdefault(arm["panel_id"], {})[arm["environment"]] = arm
    low_density = by_panel[
        "kim_2026_density_diversity:h2o:T300:rho03:rdf_similarity"
    ]
    assert low_density["density_diverse"]["outcome"]["mean_rdf_similarity"] > 0.98
    assert low_density["density_diverse"]["derived"]["panel_normalized_utility"] == 1.0
    high_density = by_panel[
        "kim_2026_density_diversity:h2o:T700:rho10:rdf_similarity"
    ]
    assert (
        high_density["no_variance"]["outcome"]["mean_rdf_similarity"]
        > high_density["density_diverse"]["outcome"]["mean_rdf_similarity"]
    )


def test_measurements_are_defined_from_training_and_target_conditions():
    data = payload()
    for arm in data["arms"]:
        measured = arm["pre_outcome_measurements"]
        if arm["environment"] == "density_diverse":
            assert measured["training_density_span_g_cm3"] == 0.7
            assert measured["target_density_inside_training_range"] == 1
            assert measured["closest_density_gap_g_cm3"] <= 0.3
        elif arm["evaluation_density_g_cm3"] == 0.3:
            assert measured["closest_density_gap_g_cm3"] == 0.7
