#!/usr/bin/env python3
"""Apply the frozen starting-policy endpoint qualification gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def apply_gate(score: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("contract") != "q07820-starting-policy-endpoint-qualification-v1":
        raise ValueError("unexpected starting-policy endpoint contract")
    if score.get("contract") != contract["qualifying_hit_contract"]:
        raise ValueError("qualifying-hit score uses the wrong endpoint contract")
    if not isinstance(score.get("scored_records"), list):
        raise ValueError("qualifying-hit score lacks attempt-level records")

    thresholds = contract["pass_gate"]
    qualified = [row for row in score["scored_records"] if row.get("qualifies") is True]
    molecules = Counter(str(row["canonical_smiles"]) for row in qualified)
    qualifying_attempts = len(qualified)
    unique_qualifying_molecules = len(molecules)
    maximum_count = max(molecules.values(), default=0)
    maximum_fraction = maximum_count / qualifying_attempts if qualifying_attempts else None
    checks = {
        "score_complete": score.get("status") == "complete",
        "attempt_count": score.get("attempts") == contract["sample"]["attempts"],
        "zero_infrastructure_failures": score.get("infrastructure_failures")
        == thresholds["required_infrastructure_failures"],
        "minimum_qualifying_attempts": qualifying_attempts
        >= thresholds["minimum_qualifying_attempts"],
        "minimum_unique_qualifying_molecules": unique_qualifying_molecules
        >= thresholds["minimum_unique_qualifying_molecules"],
        "maximum_single_molecule_fraction": maximum_fraction is not None
        and maximum_fraction
        <= thresholds["maximum_fraction_of_qualifying_attempts_from_one_canonical_molecule"],
    }
    passed = all(checks.values())
    return {
        "schema_version": "1.0",
        "contract": contract["contract"],
        "status": "passed" if passed else "failed",
        "authorizes_matched_training": passed,
        "checks": checks,
        "attempts": score.get("attempts"),
        "infrastructure_failures": score.get("infrastructure_failures"),
        "qualifying_attempts": qualifying_attempts,
        "qualifying_attempt_rate": (
            qualifying_attempts / score["attempts"] if score.get("attempts") else None
        ),
        "unique_qualifying_molecules": unique_qualifying_molecules,
        "maximum_qualifying_attempts_from_one_molecule": maximum_count,
        "maximum_fraction_of_qualifying_attempts_from_one_molecule": maximum_fraction,
        "failed_endpoint_check_counts": score.get("failed_gate_counts", {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score = json.loads(args.score.read_text())
    contract = json.loads(args.contract.read_text())
    result = apply_gate(score, contract)
    result["inputs"] = {
        "qualifying_hit_score_sha256": sha256_file(args.score),
        "starting_policy_endpoint_contract_sha256": sha256_file(args.contract),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
