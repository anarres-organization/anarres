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
    if contract.get("contract") not in {
        "q07820-starting-policy-endpoint-qualification-v1",
        "q07820-starting-policy-endpoint-qualification-v2",
    }:
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


def validate_evidence_chain(
    score: dict[str, Any],
    contract: dict[str, Any],
    sample_path: Path,
    docking_report: dict[str, Any],
    metrics_report: dict[str, Any],
) -> None:
    attempts = contract["sample"]["attempts"]
    sample_sha256 = sha256_file(sample_path)
    checks = {
        "docking_contract": docking_report.get("contract") == contract["contract"],
        "docking_complete": docking_report.get("status") == "complete",
        "docking_attempts": docking_report.get("attempts") == attempts,
        "sample_identity": docking_report.get("inputs", {}).get("samples_sha256") == sample_sha256,
        "metrics_contract": metrics_report.get("contract") == contract["contract"],
        "metrics_complete": metrics_report.get("status") == "complete",
        "metrics_attempts": metrics_report.get("attempts") == attempts,
        "docking_to_metrics": metrics_report.get("inputs", {}).get("docking_records_sha256")
        == docking_report.get("output_records_sha256"),
        "metrics_to_score": score.get("inputs", {}).get("records_sha256")
        == metrics_report.get("output_records_sha256"),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise ValueError(f"endpoint evidence chain failed: {', '.join(failures)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--docking-report", type=Path, required=True)
    parser.add_argument("--metrics-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    score = json.loads(args.score.read_text())
    contract = json.loads(args.contract.read_text())
    docking_report = json.loads(args.docking_report.read_text())
    metrics_report = json.loads(args.metrics_report.read_text())
    validate_evidence_chain(
        score,
        contract,
        args.sample,
        docking_report,
        metrics_report,
    )
    result = apply_gate(score, contract)
    result["inputs"] = {
        "qualifying_hit_score_sha256": sha256_file(args.score),
        "starting_policy_endpoint_contract_sha256": sha256_file(args.contract),
        "starting_policy_sample_sha256": sha256_file(args.sample),
        "docking_report_sha256": sha256_file(args.docking_report),
        "endpoint_metrics_report_sha256": sha256_file(args.metrics_report),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
