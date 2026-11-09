import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parent / "freeze_target_roles.py"
SPEC = importlib.util.spec_from_file_location("freeze_target_roles", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_roles_are_deterministic_disjoint_and_outcome_blind(tmp_path):
    ids = [f"mp-{index}" for index in range(91)]
    csv_path = tmp_path / "pbe.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["mp_id", "stable"])
        writer.writeheader()
        for index, material_id in enumerate(ids):
            writer.writerow({"mp_id": material_id, "stable": index % 2 == 0})
    unseen_path = tmp_path / "unseen.json"
    unseen_path.write_text(json.dumps({"not_in_mptrj": ids}), encoding="utf-8")

    first = MODULE.freeze_roles(csv_path, unseen_path)
    second = MODULE.freeze_roles(csv_path, unseen_path)
    assert first == second
    assert first["eligibility"]["split_features_used"] == ["mp_id"]
    assert {role: len(values) for role, values in first["roles"].items()} == MODULE.ROLE_SIZES
    role_sets = [set(values) for values in first["roles"].values()]
    assert sum(map(len, role_sets)) == len(set().union(*role_sets)) == 91
