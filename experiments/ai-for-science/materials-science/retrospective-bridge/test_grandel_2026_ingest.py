import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_grandel_2026", ROOT / "scripts" / "ingest_grandel_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "grandel_2026_phonon_panels.json").read_text())


def test_exact_table_values_are_preserved():
    data = payload()
    assert data["panel_count"] == 4
    assert data["arm_count"] == 12
    lookup = {(arm["training_regime"], arm["training_environment"]): arm for arm in data["arms"]}
    assert lookup[("training_from_scratch", "primitive_cell")]["outcome"] == {
        "median_phonon_frequency_mae_THz": 0.39,
        "interquartile_range_THz": 0.50,
    }
    assert lookup[("equitrain", "large_supercell")]["outcome"] == {
        "median_phonon_frequency_mae_THz": 0.05,
        "interquartile_range_THz": 0.05,
    }


def test_large_supercell_wins_within_every_training_regime():
    data = payload()
    by_panel = {}
    for arm in data["arms"]:
        by_panel.setdefault(arm["panel_id"], []).append(arm)
    assert len(by_panel) == 4
    for arms in by_panel.values():
        winner = max(arms, key=lambda arm: arm["derived"]["panel_normalized_utility"])
        assert winner["training_environment"] == "large_supercell"


def test_reference_cost_boundary_is_explicit():
    data = payload()
    assert any("more atoms" in line for line in data["interpretation_boundary"])
    assert any(
        "outside the strict matched-cost" in line for line in data["interpretation_boundary"]
    )
