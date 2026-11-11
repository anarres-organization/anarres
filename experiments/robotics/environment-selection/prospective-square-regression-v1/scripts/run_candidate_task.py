#!/usr/bin/env python3
"""Run one sealed Square candidate training and fixed-state evaluation task."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from prepare_candidate_dataset import mask_key, read_contract, validate_prepared


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_revision(checkout: Path, expected: str) -> None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=checkout, text=True, capture_output=True, check=False
    )
    if result.returncode != 0 or result.stdout.strip() != expected:
        raise ValueError(f"CuraEval checkout must be pinned to {expected}")


def command_contract(
    python: str,
    curaeval: Path,
    dataset: Path,
    protocol: dict,
    candidate_id: str,
    seed: int,
    output_dir: Path,
) -> list[str]:
    training = protocol["training"]
    return [
        python,
        str(curaeval / "scripts/run_dp.py"),
        "--dataset",
        str(dataset),
        "--filter_key",
        mask_key(candidate_id),
        "--name",
        f"dp_square_{candidate_id}_seed{seed}",
        "--output_dir",
        str(output_dir / "checkpoint"),
        "--epochs",
        str(training["epochs"]),
        "--steps_per_epoch",
        str(training["steps_per_epoch"]),
        "--batch_size",
        str(training["batch_size"]),
        "--rollout_n",
        "0",
        "--horizon",
        str(protocol["evaluation"]["horizon"]),
        "--seed",
        str(seed),
        "--fast",
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", required=True)
    parser.add_argument("--curaeval", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--state-bank", type=Path, required=True)
    parser.add_argument("--state-bank-manifest", type=Path, required=True)
    parser.add_argument("--evaluator", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()

    candidates, protocol = read_contract(args.candidates, args.protocol)
    allowed_candidates = set(candidates["candidates"]) - {"all_data_reference"}
    if args.candidate_id not in allowed_candidates:
        raise ValueError("candidate is not an unopened training arm")
    if args.seed not in protocol["training"]["candidate_seeds"]:
        raise ValueError("seed differs from the frozen candidate contract")
    validate_prepared(args.dataset, args.candidates, args.protocol)
    sources = json.loads(args.sources.read_text(encoding="utf-8"))["sources"]
    revision = next(source["revision"] for source in sources if source["name"] == "CuraEval")
    checked_revision(args.curaeval, revision)
    command = command_contract(
        args.python,
        args.curaeval,
        args.dataset,
        protocol,
        args.candidate_id,
        args.seed,
        args.output_dir,
    )
    if args.print_contract:
        print(json.dumps({"train_argv": command}, indent=2))
        return
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    contract = {
        "study_id": protocol["study_id"],
        "candidate_id": args.candidate_id,
        "seed": args.seed,
        "candidate_membership_sha256": candidates["candidates"][args.candidate_id][
            "membership_sha256"
        ],
        "candidates_sha256": sha256(args.candidates),
        "protocol_sha256": sha256(args.protocol),
        "prepared_dataset_sha256": sha256(args.dataset),
        "train_argv": command,
    }
    (args.output_dir / "TASK_CONTRACT.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    env = os.environ.copy()
    with (args.output_dir / "train.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    checkpoints = list((args.output_dir / "checkpoint").rglob("last.pth"))
    if len(checkpoints) != 1:
        raise ValueError(f"expected one final checkpoint, found {len(checkpoints)}")
    checkpoint = checkpoints[0]
    (args.output_dir / "checkpoint.sha256").write_text(
        f"{sha256(checkpoint)}  {checkpoint}\n", encoding="utf-8"
    )
    (args.output_dir / "TRAIN_COMPLETE").touch()

    evaluation = args.output_dir / "evaluation.json"
    eval_command = [
        args.python,
        str(args.evaluator),
        "--agent",
        str(checkpoint),
        "--state-bank",
        str(args.state_bank),
        "--state-bank-manifest",
        str(args.state_bank_manifest),
        "--protocol",
        str(args.protocol),
        "--policy-id",
        args.candidate_id,
        "--training-seed",
        str(args.seed),
        "--output",
        str(evaluation),
    ]
    with (args.output_dir / "evaluate.log").open("w", encoding="utf-8") as log:
        subprocess.run(eval_command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    (args.output_dir / "evaluation.sha256").write_text(
        f"{sha256(evaluation)}  {evaluation}\n", encoding="utf-8"
    )
    (args.output_dir / "EVAL_COMPLETE").touch()


if __name__ == "__main__":
    main()
