import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_baghishov_2026", ROOT / "scripts" / "ingest_baghishov_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_baghishov_derived_artifact():
    import json

    payload = json.loads((ROOT / "data" / "baghishov_2026_leverage_panels.json").read_text())
    assert payload["panel_count"] == 18
    assert payload["arm_count"] == 54
    assert len(payload["arms"]) == 54
    for budget in MODULE.BUDGETS:
        energy = [
            arm for arm in payload["arms"]
            if arm["training_configuration_count"] == budget and arm["endpoint"] == "testing_energy_rmse"
        ]
        force = [
            arm for arm in payload["arms"]
            if arm["training_configuration_count"] == budget and arm["endpoint"] == "testing_force_rmse"
        ]
        assert min(energy, key=lambda arm: arm["outcome"]["mean_rmse"])["sampling_method"] == "Leverage"
        assert min(force, key=lambda arm: arm["outcome"]["mean_rmse"])["sampling_method"] == "Block Leverage"
