import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent / "verify_candidate_bank.py"
SPEC = importlib.util.spec_from_file_location("verify_candidate_bank", SCRIPT)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def bank():
    candidate = {
        "candidate_id": "source__rule",
        "records": 1,
        "atoms": 2,
        "neighbor_edges": 4,
        "neighbor_edges_per_atom": 2.0,
        "parents": 1,
        "chemical_systems": 1,
        "parent_prototypes": 1,
        "signal_density_per_atom": 1.0,
        "effective_signal_coverage": 1.0,
        "chemical_system_entropy": 0.0,
        "mean_target_affinity": 0.5,
        "membership_sha256": "0" * 64,
        "record_indices": [0],
    }
    return {
        "inputs": {"measurement_sha256": {"records.jsonl": "1" * 64}},
        "construction": {"atom_budget_per_candidate": 2},
        "candidates": [candidate],
    }


def test_roundoff_is_accepted_but_membership_changes_are_rejected():
    released = bank()
    reproduced = deepcopy(released)
    reproduced["candidates"][0]["mean_target_affinity"] += 1e-14
    report = MODULE.verify(released, reproduced)
    assert report["memberships_exact"]

    changed = deepcopy(reproduced)
    changed["candidates"][0]["record_indices"] = [1]
    with pytest.raises(ValueError, match="record_indices"):
        MODULE.verify(released, changed)
