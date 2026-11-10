#!/usr/bin/env python3
"""Verify the sealed Square execution matrix before opening candidate outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recorded_hash(path: Path) -> tuple[str, Path]:
    fields = path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    if len(fields) != 2 or len(fields[0]) != 64:
        raise ValueError(f"invalid hash record: {path}")
    return fields[0], Path(fields[1])


def gate_record(
    execution_path: Path,
    candidates_path: Path,
    protocol_path: Path,
    prepared_dataset: Path,
    runs_root: Path,
) -> dict:
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if execution.get("candidate_outcomes_opened") is not False:
        raise ValueError("execution freeze does not preserve sealed candidate outcomes")
    if execution["inputs"]["CANDIDATES.json"] != sha256(candidates_path):
        raise ValueError("candidate panel differs from the execution freeze")
    if execution["inputs"]["PROTOCOL.json"] != sha256(protocol_path):
        raise ValueError("protocol differs from the execution freeze")

    expected_pairs = {
        (row["candidate_id"], row["seed"]): row for row in execution["candidate_runs"]
    }
    if len(expected_pairs) != execution["expected_candidate_runs"]:
        raise ValueError("execution freeze contains duplicate or missing runs")
    observed_dirs = {path.name for path in runs_root.iterdir() if path.is_dir()}
    expected_dirs = {row["run_id"] for row in execution["candidate_runs"]}
    if observed_dirs != expected_dirs:
        raise ValueError("run directories differ from the frozen execution matrix")

    prepared_sha256 = sha256(prepared_dataset)
    expected_episodes = (
        protocol["evaluation"]["states"] * protocol["evaluation"]["rollout_replicates_per_state"]
    )
    expected_state_replicates = {
        (state_id, replicate)
        for state_id in range(protocol["evaluation"]["states"])
        for replicate in range(protocol["evaluation"]["rollout_replicates_per_state"])
    }
    records = []
    checkpoint_hashes = set()
    total_episodes = 0
    for row in execution["candidate_runs"]:
        run = runs_root / row["run_id"]
        required = (
            "TASK_CONTRACT.json",
            "TRAIN_COMPLETE",
            "checkpoint.sha256",
            "evaluation.json",
            "evaluation.sha256",
            "EVAL_COMPLETE",
        )
        if any(not (run / name).is_file() for name in required):
            raise ValueError(f"run is incomplete: {row['run_id']}")
        contract = json.loads((run / "TASK_CONTRACT.json").read_text(encoding="utf-8"))
        if (
            contract.get("study_id") != execution["study_id"]
            or contract.get("candidate_id") != row["candidate_id"]
            or contract.get("seed") != row["seed"]
            or contract.get("candidate_membership_sha256") != row["membership_sha256"]
            or contract.get("candidates_sha256") != execution["inputs"]["CANDIDATES.json"]
            or contract.get("protocol_sha256") != execution["inputs"]["PROTOCOL.json"]
            or contract.get("prepared_dataset_sha256") != prepared_sha256
        ):
            raise ValueError(f"task contract differs from the freeze: {row['run_id']}")

        checkpoint_expected, checkpoint = recorded_hash(run / "checkpoint.sha256")
        if not checkpoint.is_file() or sha256(checkpoint) != checkpoint_expected:
            raise ValueError(f"checkpoint hash mismatch: {row['run_id']}")
        checkpoint_hashes.add(checkpoint_expected)
        evaluation_expected, evaluation_path = recorded_hash(run / "evaluation.sha256")
        if evaluation_path != run / "evaluation.json":
            raise ValueError(f"evaluation path mismatch: {row['run_id']}")
        if sha256(evaluation_path) != evaluation_expected:
            raise ValueError(f"evaluation hash mismatch: {row['run_id']}")

        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        observed_state_replicates = {
            (record["state_id"], record["replicate"]) for record in evaluation["records"]
        }
        if (
            evaluation.get("study_id") != execution["study_id"]
            or evaluation.get("policy_id") != row["candidate_id"]
            or evaluation.get("training_seed") != row["seed"]
            or evaluation.get("checkpoint_sha256") != checkpoint_expected
            or evaluation.get("episodes") != expected_episodes
            or len(evaluation["records"]) != expected_episodes
            or observed_state_replicates != expected_state_replicates
            or evaluation.get("exceptions") != 0
        ):
            raise ValueError(f"evaluation contract mismatch: {row['run_id']}")
        total_episodes += expected_episodes
        records.append(
            {
                "run_id": row["run_id"],
                "task_contract_sha256": sha256(run / "TASK_CONTRACT.json"),
                "checkpoint_sha256": checkpoint_expected,
                "evaluation_sha256": evaluation_expected,
            }
        )

    if len(checkpoint_hashes) != execution["expected_candidate_runs"]:
        raise ValueError("candidate runs do not have distinct checkpoints")
    if total_episodes != execution["expected_candidate_evaluation_episodes"]:
        raise ValueError("evaluation episode count differs from the execution freeze")
    return {
        "schema_version": "anarres.robotics-square-release-gate.v1",
        "study_id": execution["study_id"],
        "status": "CANDIDATE_RESULTS_COMPLETE__OUTCOMES_UNOPENED",
        "candidate_outcomes_opened": False,
        "execution_freeze_sha256": sha256(execution_path),
        "prepared_dataset_sha256": prepared_sha256,
        "candidate_runs": len(records),
        "evaluation_episodes": total_episodes,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-freeze", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--prepared-dataset", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = gate_record(
        args.execution_freeze,
        args.candidates,
        args.protocol,
        args.prepared_dataset,
        args.runs_root,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_runs": result["candidate_runs"],
                "evaluation_episodes": result["evaluation_episodes"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
