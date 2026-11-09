import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "ingest_varga_umbrich_2026_force_ntk",
    ROOT / "scripts" / "ingest_varga_umbrich_2026_force_ntk.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def payload() -> dict:
    path = ROOT / "data" / "varga_umbrich_2026_force_ntk_panels.json"
    return json.loads(path.read_text())


def test_table_one_becomes_twelve_matched_multiarm_panels():
    data = payload()
    assert data["panel_count"] == 12
    assert data["arm_count"] == 84
    panels = {}
    for arm in data["arms"]:
        panels.setdefault(arm["panel_id"], []).append(arm)
        assert arm["outcome"]["independent_experiment_seeds"] == 2
    assert {len(arms) for arms in panels.values()} == {7}


def test_exact_table_values_and_winners_are_preserved():
    data = payload()
    values = {(arm["dataset"], arm["metric"], arm["environment"]): arm for arm in data["arms"]}
    assert values[("t1x", "energy_rmse_auc", "ntk_energy")]["outcome"]["reported_error"] == 159.5
    assert (
        values[("pmechdb", "final_force_rmse", "committee_force")]["outcome"]["reported_error"]
        == 102.0
    )
    assert (
        values[("rgd", "energy_rmse_auc", "activation")]["derived"]["panel_normalized_regret"]
        == 0.0
    )


def test_ingest_rejects_a_different_paper_file(tmp_path):
    wrong = tmp_path / "paper.pdf"
    wrong.write_bytes(b"not the audited paper")
    try:
        MODULE.ingest(paper_pdf=wrong)
    except ValueError as error:
        assert "checksum mismatch" in str(error)
    else:
        raise AssertionError("expected checksum verification to fail")
