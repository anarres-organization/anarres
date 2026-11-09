import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_lee_2026", ROOT / "scripts" / "ingest_lee_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "lee_2026_training_regime_panels.json").read_text())


def test_exact_supplementary_table_values_are_preserved():
    data = payload()
    assert data["panel_count"] == 2
    assert data["arm_count"] == 6
    by_regime = {}
    for arm in data["arms"]:
        by_regime.setdefault(arm["training_regime"], {})[arm["environment"]] = arm
    assert by_regime["scratch"]["lcmd"]["outcome"]["log_diffusivity_r2"] == 0.70
    assert by_regime["fine_tuning"]["direct"]["outcome"]["log_diffusivity_r2"] == 0.56
    assert (
        by_regime["fine_tuning"]["random"]["outcome"][
            "bootstrap_log_diffusivity_r2_standard_deviation"
        ]
        == 0.28
    )


def test_regime_reversal_survives_label_cost_normalization():
    data = payload()
    for regime, expected in (("scratch", "lcmd"), ("fine_tuning", "direct")):
        arms = [arm for arm in data["arms"] if arm["training_regime"] == regime]
        raw = max(arms, key=lambda arm: arm["derived"]["panel_normalized_utility"])
        adjusted = max(arms, key=lambda arm: arm["derived"]["cost_adjusted_normalized_utility"])
        assert raw["environment"] == expected
        assert adjusted["environment"] == expected


def test_budget_mismatch_is_explicit():
    data = payload()
    budgets = {
        arm["environment"]: arm["pre_outcome_measurements"]["dft_label_budget"]
        for arm in data["arms"]
        if arm["training_regime"] == "scratch"
    }
    assert budgets == {"direct": 8879, "lcmd": 8000, "random": 8000}
    assert any("not exactly equal" in line for line in data["interpretation_boundary"])
