from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "score_endpoint_metrics.py"
SPEC = importlib.util.spec_from_file_location("score_endpoint_metrics", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_expands_complete_and_scientific_zero_records() -> None:
    docking = [
        {
            "attempt_id": "a",
            "canonical_smiles": "CCO",
            "infrastructure_status": "ok",
            "docking_status": "ok",
            "vina_affinity": -9.0,
            "pose_sdf": "pose.sdf",
            "reason": None,
        },
        {
            "attempt_id": "b",
            "canonical_smiles": "CCC",
            "infrastructure_status": "ok",
            "docking_status": "scientific_zero",
            "vina_affinity": None,
            "pose_sdf": None,
            "reason": "ligand_conformer_failure",
        },
    ]
    metrics = {
        "CCO": {
            "valid": True,
            "qed": 0.7,
            "synthetic_accessibility": 2.0,
            "chemical_filters_pass": True,
            "posebusters_all_valid": True,
            "strain_energy": 20.0,
            "clash_score": 1.0,
            "pose_metric_status": "complete",
            "reason": None,
        }
    }
    rows = MODULE.expand_endpoint_records(docking, metrics, {"CCO": 0.8})

    assert rows[0]["valid"] is True
    assert rows[0]["interaction_score"] == 0.8
    assert rows[1]["valid"] is False
    assert rows[1]["interaction_score"] is None
    assert rows[1]["reason"] == "ligand_conformer_failure"


def test_flattens_native_interaction_columns() -> None:
    class Row:
        @staticmethod
        def items():
            return [
                (("UNL1", "LEU15.A", "HBAcceptor"), True),
                (("UNL1", "GLY16.A", "VdWContact"), False),
            ]

    assert MODULE.flatten_interaction_row(Row()) == {
        "LEU15.A_HBAcceptor": True,
        "GLY16.A_VdWContact": False,
    }


def test_normalizes_non_python_chemical_filter_boolean() -> None:
    class Truthy:
        @staticmethod
        def __bool__() -> bool:
            return True

    assert MODULE.chemical_filter_pass({"ChemFilter": Truthy()}) is True
    assert MODULE.chemical_filter_pass({"ChemFilter": False}) is False
    assert MODULE.chemical_filter_pass(False) is False


def test_interaction_preparation_preserves_retained_record_identities() -> None:
    class Metric:
        @staticmethod
        def _prepare_ligands(records):
            return [] if records == ["drop"] else records

        @staticmethod
        def _filter_ligands(ligands):
            return ligands

    records = [("keep-a", "a"), ("drop", "drop"), ("keep-b", "b")]
    assert MODULE.interaction_ready_records(Metric(), records) == [
        ("keep-a", "a"),
        ("keep-b", "b"),
    ]
