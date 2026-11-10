#!/usr/bin/env python3
"""Bind the qualified Square candidates to the exact unopened execution matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from prepare_candidate_dataset import read_contract


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(
    candidates_path: Path,
    protocol_path: Path,
    scoring_contract_path: Path,
    sources_path: Path,
    state_bank_path: Path,
    state_bank_manifest_path: Path,
    scripts: list[Path],
) -> dict:
    candidates, protocol = read_contract(candidates_path, protocol_path)
    scoring = json.loads(scoring_contract_path.read_text(encoding="utf-8"))
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    state_manifest = json.loads(state_bank_manifest_path.read_text(encoding="utf-8"))
    if scoring.get("candidate_outcomes_opened") is not False:
        raise ValueError("scoring contract does not preserve sealed candidate outcomes")
    if scoring["study_id"] != protocol["study_id"]:
        raise ValueError("scoring contract belongs to a different study")
    if sha256(state_bank_path) != state_manifest["state_bank_sha256"]:
        raise ValueError("state bank differs from its frozen manifest")
    revision = next(
        source["revision"] for source in sources["sources"] if source["name"] == "CuraEval"
    )
    candidate_ids = [
        candidate_id
        for candidate_id in scoring["comparison_arms"]
        if candidate_id != "all_data_reference"
    ]
    matrix = [
        {
            "run_id": f"{candidate_id}__seed-{seed}",
            "candidate_id": candidate_id,
            "seed": seed,
            "membership_sha256": candidates["candidates"][candidate_id]["membership_sha256"],
            "evaluation_episodes": (
                protocol["evaluation"]["states"]
                * protocol["evaluation"]["rollout_replicates_per_state"]
            ),
        }
        for candidate_id in candidate_ids
        for seed in protocol["training"]["candidate_seeds"]
    ]
    expected_runs = len(candidate_ids) * len(protocol["training"]["candidate_seeds"])
    if (
        len(matrix) != expected_runs
        or expected_runs != scoring["integrity"]["required_candidate_policies"]
    ):
        raise ValueError("execution matrix differs from the scoring contract")
    return {
        "schema_version": "anarres.robotics-square-execution-freeze.v1",
        "study_id": protocol["study_id"],
        "status": "EXECUTION_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
        "candidate_outcomes_opened": False,
        "point_prediction": scoring["point_prediction"],
        "curaeval_revision": revision,
        "source_dataset_sha256": protocol["source"]["dataset_sha256"],
        "expected_candidate_runs": expected_runs,
        "expected_candidate_evaluation_episodes": sum(run["evaluation_episodes"] for run in matrix),
        "candidate_runs": matrix,
        "inputs": {
            "CANDIDATES.json": sha256(candidates_path),
            "PROTOCOL.json": sha256(protocol_path),
            "SCORING_CONTRACT.json": sha256(scoring_contract_path),
            "SOURCES.json": sha256(sources_path),
            "STATE_BANK.hdf5": sha256(state_bank_path),
            "STATE_BANK.json": sha256(state_bank_manifest_path),
            **{f"scripts/{script.name}": sha256(script) for script in scripts},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--scoring-contract", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--state-bank", type=Path, required=True)
    parser.add_argument("--state-bank-manifest", type=Path, required=True)
    parser.add_argument("--scripts", nargs="+", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = build(
        args.candidates,
        args.protocol,
        args.scoring_contract,
        args.sources,
        args.state_bank,
        args.state_bank_manifest,
        args.scripts,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "expected_candidate_runs": result["expected_candidate_runs"],
                "expected_candidate_evaluation_episodes": result[
                    "expected_candidate_evaluation_episodes"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
