import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_varga_umbrich_2026",
    ROOT / "scripts" / "ingest_varga_umbrich_2026.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "varga_umbrich_2026_transfer_panels.json").read_text())


def test_transfer_table_is_reconstructed_as_paired_decisions():
    data = payload()
    assert data["panel_count"] == 36
    assert data["arm_count"] == 72
    panels = {}
    for arm in data["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
        assert arm["outcome"]["independent_experiment_seeds"] == 2
    assert {len(arms) for arms in panels.values()} == {2}
    assert all("paired_random" in {arm["environment"] for arm in arms} for arms in panels.values())


def test_exact_positive_and_negative_round_gains_are_preserved():
    data = payload()
    values = {
        (arm["comparison_method"], arm["dataset"], arm["metric"], arm["environment"]): arm[
            "outcome"
        ]["round_gain_percent_vs_paired_random"]
        for arm in data["arms"]
    }
    assert values[("ntk_lcmd", "t1x_mixed", "energy_rmse", "ntk_lcmd")] == 83.3
    assert values[("committee_energy", "pmechdb", "energy_mae", "committee_energy")] == -31.6
    assert values[("activation_lcmd", "rgd", "force_mae", "paired_random")] == 0.0


def test_method_specific_targets_are_never_combined_into_multiarm_panels():
    data = payload()
    for arm in data["arms"]:
        if arm["environment"] != "paired_random":
            assert arm["environment"] == arm["comparison_method"]
