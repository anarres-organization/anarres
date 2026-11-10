from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "derive_qualifying_hit_thresholds.py"
SPEC = importlib.util.spec_from_file_location("derive_qualifying_hit_thresholds", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_csv(
    path: Path,
    column: str,
    values: list[object],
    posebusters: list[object] | None = None,
) -> None:
    fieldnames = [column]
    if posebusters is not None:
        fieldnames.append("PoseBusterAllValid")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, value in enumerate(values):
            row = {column: value}
            if posebusters is not None:
                row["PoseBusterAllValid"] = posebusters[index]
            writer.writerow(row)


def test_percentile_uses_linear_interpolation() -> None:
    assert MODULE.percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert MODULE.percentile([1.0, 2.0, 3.0, 4.0], 0.75) == 3.25


def test_derives_thresholds_and_preserves_missing_values(tmp_path: Path) -> None:
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"contract": "q07820-qualifying-hit-v1", "target_id": "Q07820"}))
    sdf = tmp_path / "actives.sdf"
    sdf.write_text(
        "mol1\n>  <vina_dock>\n-9.0\n\n$$$$\n"
        "mol2\n>  <vina_dock>\nnan\n\n$$$$\n"
        "mol3\n>  <vina_dock>\n-7.0\n\n$$$$\n"
    )
    interactions = tmp_path / "interactions.csv"
    strain = tmp_path / "strain.csv"
    clashes = tmp_path / "clashes.csv"
    write_csv(interactions, "InteractionScore", [0.1, "", 0.9])
    write_csv(
        strain,
        "StrainEnergy",
        [1.0, 2.0, 3.0, 4.0],
        [True, False, True, True],
    )
    write_csv(clashes, "ClashScore", [0.0, 1.0, "bad", 3.0])

    result = MODULE.derive(contract, sdf, interactions, strain, clashes)

    assert result["reference_summaries"]["vina_affinity"]["rows"] == 3
    assert result["reference_summaries"]["vina_affinity"]["finite"] == 2
    assert result["instantiated_thresholds"]["vina_affinity_maximum"] == -8.0
    assert result["instantiated_thresholds"]["interaction_score_minimum"] == 0.5
    assert result["instantiated_thresholds"]["strain_energy_maximum"] == 3.25
    assert result["instantiated_thresholds"]["clash_score_maximum"] == 2.0
    assert result["reference_summaries"]["posebusters_all_valid"]["passed"] == 3
    assert result["candidate_or_trained_policy_outcomes_read"] is False
