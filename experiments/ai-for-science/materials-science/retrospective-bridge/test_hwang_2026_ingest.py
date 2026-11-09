import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_hwang_2026", ROOT / "scripts" / "ingest_hwang_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "hwang_2026_training_regime_panels.json").read_text())


def test_all_exact_matched_budgets_and_endpoints_are_preserved():
    data = payload()
    assert data["panel_count"] == 18
    assert data["arm_count"] == 36
    assert data["matched_contract"]["matched_training_configuration_counts"] == {
        "Au": [40, 200, 2000],
        "RuO2": [50, 100, 300],
        "BiVO4": [100, 200, 592],
    }
    panels = {decision["panel_id"] for decision in data["matched_decisions"]}
    assert len(panels) == 3 * 3 * 2


def test_released_source_values_are_reconstructed_exactly():
    data = payload()
    lookup = {
        (
            decision["formula"],
            decision["training_configuration_count"],
            decision["endpoint"],
        ): decision
        for decision in data["matched_decisions"]
    }
    assert lookup[("Au", 40, "energy_rmse")]["fine_tuning_rmse"] == 4.3
    assert lookup[("Au", 2000, "force_rmse")]["training_from_scratch_rmse"] == 29.7
    assert lookup[("RuO2", 100, "force_rmse")]["fine_tuning_rmse"] == 174.6
    assert lookup[("BiVO4", 592, "energy_rmse")]["training_from_scratch_rmse"] == 12.2


def test_fine_tuning_wins_every_matched_panel():
    data = payload()
    assert all(decision["winner"] == "fine_tuning" for decision in data["matched_decisions"])


def test_update_regime_boundary_is_explicit():
    data = payload()
    assert any("update regime changes" in line for line in data["interpretation_boundary"])
    assert any(
        "outside the strict fitted bridge" in line for line in data["interpretation_boundary"]
    )
