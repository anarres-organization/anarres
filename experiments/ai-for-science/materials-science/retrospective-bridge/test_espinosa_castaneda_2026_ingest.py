import importlib.util
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_espinosa_castaneda_2026",
    ROOT / "scripts" / "ingest_espinosa_castaneda_2026.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_diversity_panels_are_matched_and_complete():
    payload = json.loads(
        (ROOT / "data" / "espinosa_castaneda_2026_diversity_panels.json").read_text()
    )
    assert payload["panel_count"] == 256
    assert payload["arm_count"] == 1504
    panels = {}
    for arm in payload["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
        assert arm["outcome"]["independent_campaign_seeds"] == 5
        assert arm["outcome"]["last_training_fraction"] == 1.0
        assert arm["pre_outcome_measurements"]["final_training_fraction"] == 1.0
    assert len(panels) == 256
    assert {len(arms) for arms in panels.values()} == {5, 6}


def test_random_arms_define_zero_paired_improvement():
    payload = json.loads(
        (ROOT / "data" / "espinosa_castaneda_2026_diversity_panels.json").read_text()
    )
    random_arms = [arm for arm in payload["arms"] if arm["environment"] == "random"]
    assert len(random_arms) == payload["panel_count"]
    assert all(
        abs(arm["outcome"]["mean_percent_improvement_vs_paired_random"]) < 1e-12
        for arm in random_arms
    )


def test_reconstruction_matches_reported_dft_qbc_aggregates():
    payload = json.loads(
        (ROOT / "data" / "espinosa_castaneda_2026_diversity_panels.json").read_text()
    )
    arms = [
        arm
        for arm in payload["arms"]
        if arm["data_regime"] == "computed_dft"
        and arm["downstream_model"] == "rf"
        and arm["environment"] == "qbc"
        and arm["pre_outcome_measurements"]["target_property_count"] == 1
    ]
    targeted = [
        arm["outcome"]["mean_percent_improvement_vs_paired_random"]
        for arm in arms
        if arm["evaluation_property_is_targeted"]
    ]
    untargeted = [
        arm["outcome"]["mean_percent_improvement_vs_paired_random"]
        for arm in arms
        if not arm["evaluation_property_is_targeted"]
    ]
    assert abs(statistics.fmean(targeted) - 6.642) < 0.001
    assert abs(statistics.fmean(untargeted) - (-2.331)) < 0.001
