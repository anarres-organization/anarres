#!/usr/bin/env python3
"""Recompute the released MLIP bank from all native pre-training records."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

STUDY = Path(__file__).resolve().parent
CONSTRUCTOR_PATH = STUDY / "construct_candidate_bank.py"
SPEC = importlib.util.spec_from_file_location("mlip_candidate_constructor", CONSTRUCTOR_PATH)
assert SPEC is not None
CONSTRUCTOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CONSTRUCTOR)

NUMERIC_FIELDS = (
    "neighbor_edges_per_atom",
    "signal_density_per_atom",
    "effective_signal_coverage",
    "chemical_system_entropy",
    "mean_target_affinity",
)


def verify(released: dict, reproduced: dict, tolerance: float = 1e-12) -> dict:
    if released["inputs"] != reproduced["inputs"]:
        raise ValueError("candidate-bank input identities differ")
    if released["construction"] != reproduced["construction"]:
        raise ValueError("candidate-bank construction contract differs")
    expected = {candidate["candidate_id"]: candidate for candidate in released["candidates"]}
    observed = {candidate["candidate_id"]: candidate for candidate in reproduced["candidates"]}
    if expected.keys() != observed.keys():
        raise ValueError("candidate identities differ")
    maximum_numeric_difference = 0.0
    for candidate_id in sorted(expected):
        left = expected[candidate_id]
        right = observed[candidate_id]
        for field in (
            "records",
            "atoms",
            "neighbor_edges",
            "parents",
            "chemical_systems",
            "parent_prototypes",
            "membership_sha256",
            "record_indices",
        ):
            if left[field] != right[field]:
                raise ValueError(f"{candidate_id} differs in {field}")
        for field in NUMERIC_FIELDS:
            difference = abs(float(left[field]) - float(right[field]))
            maximum_numeric_difference = max(maximum_numeric_difference, difference)
            if not math.isclose(
                float(left[field]), float(right[field]), rel_tol=tolerance, abs_tol=tolerance
            ):
                raise ValueError(f"{candidate_id} differs in {field} by {difference}")
    return {
        "status": "pass",
        "measurement_records": 80_000,
        "measurement_shards": len(released["inputs"]["measurement_sha256"]),
        "candidates": len(expected),
        "memberships_exact": True,
        "maximum_numeric_difference": maximum_numeric_difference,
        "numeric_tolerance": tolerance,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--measurements", type=Path, nargs="+", required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--target-yaml-dir", type=Path, required=True)
    parser.add_argument("--bank", type=Path, default=STUDY / "CANDIDATE_BANK_DRAFT.json")
    args = parser.parse_args()
    released = json.loads(args.bank.read_text(encoding="utf-8"))
    reproduced = CONSTRUCTOR.construct(
        args.manifest,
        sorted(args.measurements),
        args.target_roles,
        args.target_yaml_dir,
        released["construction"]["atom_budget_per_candidate"],
    )
    print(json.dumps(verify(released, reproduced), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
