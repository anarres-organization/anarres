import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "ingest_kulichenko_2023.py"
SPEC = importlib.util.spec_from_file_location("kulichenko_ingest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reconstructs_complete_cross_test_matrix():
    payload = MODULE.reconstruct()
    assert payload["panel_count"] == 4
    assert payload["arm_count"] == 16
    panels = {}
    for arm in payload["arms"]:
        panels.setdefault(arm["target_environment"], []).append(arm)
    assert min(
        panels["md1000"], key=lambda arm: arm["outcome"]["energy_rmse_kcal_per_mol"]
    )["training_environment"] == "md1000"
    assert min(
        panels["md600"], key=lambda arm: arm["outcome"]["energy_rmse_kcal_per_mol"]
    )["training_environment"] == "udd350"
    for arms in panels.values():
        utilities = [arm["derived"]["panel_normalized_utility"] for arm in arms]
        assert min(utilities) == 0.0
        assert max(utilities) == 1.0
