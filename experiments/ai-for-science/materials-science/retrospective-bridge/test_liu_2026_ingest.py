import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_liu_2026", ROOT / "scripts" / "ingest_liu_2026.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads((ROOT / "data" / "liu_2026_tungsten_label_panels.json").read_text())


def test_released_notebook_yields_two_complete_panels():
    data = payload()
    assert data["panel_count"] == 2
    assert data["arm_count"] == 12
    assert all(arm["outcome"]["independent_initializations"] == 5 for arm in data["arms"])


def test_exact_replicate_values_and_cost_coordinates():
    data = payload()
    lookup = {(arm["endpoint"], arm["environment"]): arm for arm in data["arms"]}
    assert lookup[("energy_rmse_eV_per_atom", "full_dft")]["outcome"]["replicate_rmse"] == [
        0.006443,
        0.006662,
        0.007506,
        0.005812,
        0.007156,
    ]
    uc1 = lookup[("force_rmse_eV_per_A", "uc_1")]
    assert uc1["pre_outcome_measurements"]["dft_atomic_environment_fraction"] == (
        0.04274561880042655
    )
    assert uc1["pre_outcome_measurements"]["matches_independently_validated_uc1_threshold"] == 1


def test_interpretation_boundary_separates_training_and_reference_cost():
    data = payload()
    assert any("label provenance" in line for line in data["interpretation_boundary"])
    assert any("source-level stress test" in line for line in data["interpretation_boundary"])
