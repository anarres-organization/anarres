from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "dock_endpoint_panel.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("dock_endpoint_panel", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_expands_duplicates_and_missing_attempts(monkeypatch) -> None:
    monkeypatch.setattr(MODULE, "canonical_smiles", lambda value: value or None)
    samples = [{"smiles": "CCO"}, {"smiles": "CCO"}, {"smiles": "CCC"}]
    results = {
        "CCO": {"status": "ok", "affinity": -8.0, "pose_sdf": "a.sdf"},
        "CCC": {
            "status": "scientific_zero",
            "reason": "ligand_conformer_failure",
            "pose_sdf": None,
        },
    }

    records = MODULE.expand_attempt_records(samples, 4, 20261126, results)

    assert len(records) == 4
    assert records[0]["vina_affinity"] == records[1]["vina_affinity"] == -8.0
    assert records[2]["docking_status"] == "scientific_zero"
    assert records[3]["reason"] == "invalid_generated_trajectory"
    assert all(item["infrastructure_status"] == "ok" for item in records)


def test_marks_infrastructure_failure(monkeypatch) -> None:
    monkeypatch.setattr(MODULE, "canonical_smiles", lambda value: value)
    records = MODULE.expand_attempt_records(
        [{"smiles": "CCO"}],
        1,
        1,
        {"CCO": {"status": "infrastructure_failure", "reason": "timeout"}},
    )
    assert records[0]["infrastructure_status"] == "failure"


def test_panel_accepts_an_explicit_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "panel",
            "--samples",
            "samples.jsonl",
            "--prepared-target",
            "target",
            "--attempts",
            "1",
            "--sample-seed",
            "7",
            "--contract",
            "q07820-starting-policy-endpoint-qualification-v2",
            "--output-dir",
            "output",
            "--output-records",
            "records.jsonl",
            "--report",
            "report.json",
        ],
    )
    args = MODULE.build_parser().parse_args()
    assert args.contract == "q07820-starting-policy-endpoint-qualification-v2"
