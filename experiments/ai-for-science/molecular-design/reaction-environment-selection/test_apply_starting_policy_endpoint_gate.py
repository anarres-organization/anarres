from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "apply_starting_policy_endpoint_gate.py"
SPEC = importlib.util.spec_from_file_location("apply_starting_policy_endpoint_gate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def contract() -> dict:
    return {
        "contract": "q07820-starting-policy-endpoint-qualification-v1",
        "qualifying_hit_contract": "q07820-qualifying-hit-v1",
        "sample": {"attempts": 16},
        "pass_gate": {
            "required_infrastructure_failures": 0,
            "minimum_qualifying_attempts": 4,
            "minimum_unique_qualifying_molecules": 2,
            "maximum_fraction_of_qualifying_attempts_from_one_canonical_molecule": 0.75,
        },
    }


def score(smiles: list[str]) -> dict:
    return {
        "contract": "q07820-qualifying-hit-v1",
        "status": "complete",
        "attempts": 16,
        "infrastructure_failures": 0,
        "failed_gate_counts": {"qed": 2},
        "scored_records": [{"canonical_smiles": value, "qualifies": True} for value in smiles]
        + [
            {"canonical_smiles": f"zero-{index}", "qualifies": False}
            for index in range(16 - len(smiles))
        ],
    }


def test_gate_passes_with_distributed_support() -> None:
    result = MODULE.apply_gate(score(["A", "A", "B", "B"]), contract())
    assert result["status"] == "passed"
    assert result["authorizes_matched_training"] is True
    assert result["qualifying_attempts"] == 4
    assert result["unique_qualifying_molecules"] == 2
    assert result["maximum_fraction_of_qualifying_attempts_from_one_molecule"] == 0.5


def test_gate_fails_concentrated_support() -> None:
    result = MODULE.apply_gate(score(["A", "A", "A", "A"]), contract())
    assert result["status"] == "failed"
    assert result["authorizes_matched_training"] is False
    assert result["checks"]["minimum_unique_qualifying_molecules"] is False
    assert result["checks"]["maximum_single_molecule_fraction"] is False
