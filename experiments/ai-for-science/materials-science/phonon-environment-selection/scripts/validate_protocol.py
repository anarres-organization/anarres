#!/usr/bin/env python3
"""Validate the prospective phonon-selection measurement protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_CANDIDATES = {
    "hash_uniform",
    "signal",
    "coverage",
    "signal_coverage",
}


def canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(protocol: dict[str, object]) -> list[str]:
    errors: list[str] = []
    candidates = set(protocol["candidate_construction"]["candidate_names"])
    if candidates != EXPECTED_CANDIDATES:
        errors.append(f"candidate names differ: {sorted(candidates)}")

    budgets = protocol["candidate_construction"]["budgets_structures"]
    if budgets != sorted(set(budgets)) or any(value <= 0 for value in budgets):
        errors.append("candidate budgets must be unique positive ascending integers")

    strata = protocol["candidate_construction"]["atom_count_strata"]
    if not strata or strata[0][0] != 1 or strata[-1][1] != 192:
        errors.append("atom-count strata do not span the qualified source range")
    for previous, current in zip(strata, strata[1:], strict=False):
        if previous[1] + 1 != current[0]:
            errors.append("atom-count strata must be contiguous")

    training_seeds = protocol["training"]["seeds"]
    if len(training_seeds) != len(set(training_seeds)) or len(training_seeds) < 2:
        errors.append("at least two distinct training seeds are required")

    if protocol["sealed_boundary"]["external_test_labels_inspected_for_this_study"]:
        errors.append("external test labels must remain sealed")
    if protocol["sealed_boundary"]["candidate_training_outcomes_exist"]:
        errors.append("candidate outcomes cannot exist at measurement-protocol freeze")

    measurement = protocol["measurement"]
    if measurement["coverage_definition"]["distance"] != (
        "Euclidean distance in the normalized 32-dimensional representation"
    ):
        errors.append("coverage distance changed")
    if measurement["signal_definition"]["excluded_terms"] != [
        "threshold-aware score ranking",
        "geometry-score ranking",
    ]:
        errors.append("per-structure signal exclusions changed")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "PROTOCOL.json",
    )
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    errors = validate(protocol)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"protocol_sha256={canonical_digest(protocol)}")


if __name__ == "__main__":
    main()
