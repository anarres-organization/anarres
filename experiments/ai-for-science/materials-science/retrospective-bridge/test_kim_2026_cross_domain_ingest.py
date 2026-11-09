import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "ingest_kim_2026_cross_domain.py"
SPEC = importlib.util.spec_from_file_location("kim_2026_cross_domain", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    return json.loads(
        (ROOT / "data" / "kim_2026_cross_domain_compatibility_audit.json").read_text()
    )


def arms() -> dict[str, dict]:
    return {arm["arm"]: arm for arm in payload()["arms"]}


def test_committed_artifact_matches_ingest_script():
    assert payload() == MODULE.ingest()


def test_exact_source_data_values_are_preserved():
    by_name = arms()
    assert by_name["mptrj_only"]["force_mae_eV_per_A"]["molecule_gga"] == 0.156852868
    assert (
        by_name["mptrj_spice_selective_1e-5"]["force_mae_eV_per_A"]["molecule_gga"] == 0.083644823
    )
    assert (
        by_name["mptrj_spice_dbs_selective_1e-5"]["force_mae_eV_per_A"]["molecule_gga"]
        == 0.048304002
    )


def test_cross_domain_gain_preserves_in_domain_accuracy():
    by_name = arms()
    baseline = by_name["mptrj_only"]
    combined = by_name["mptrj_spice_dbs_selective_1e-5"]
    assert (
        combined["force_mae_eV_per_A"]["molecule_gga"]
        < baseline["force_mae_eV_per_A"]["molecule_gga"]
    )
    assert (
        abs(
            combined["force_mae_eV_per_A"]["crystal_gga"]
            - baseline["force_mae_eV_per_A"]["crystal_gga"]
        )
        < 0.002
    )


def test_audit_stays_outside_fixed_trainer_bridge():
    boundaries = payload()["interpretation_boundary"]
    assert any("database membership" in line and "regularization" in line for line in boundaries)
    assert any("relabeling cost" in line for line in boundaries)
    assert any("outside the fitted bridge" in line for line in boundaries)
