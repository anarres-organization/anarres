#!/usr/bin/env python3
"""Sample one frozen molecular policy under the matched evaluation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("training manifest must be an object")
    return value


def validate_policy(
    *,
    contract: dict[str, Any],
    contract_path: Path,
    policy: Path,
    arm: str,
    training_seed: int,
    checkpoint_step: int,
    training_manifest: Path | None,
) -> dict[str, Any]:
    training = contract["training"]
    evaluation = contract["evaluation"]
    if training_seed not in training["seeds"]:
        raise ValueError("training seed is not in the frozen contract")
    if str(checkpoint_step) not in evaluation["seeds"][str(training_seed)]:
        raise ValueError("checkpoint has no frozen evaluation seed")

    policy_sha256 = sha256_file(policy)
    if checkpoint_step == 0:
        if arm != "warm_start" or training_manifest is not None:
            raise ValueError("step zero requires the shared warm_start policy")
        if policy_sha256 != contract["starting_policy"]["weights_only_sha256"]:
            raise ValueError("warm-start policy differs from the frozen artifact")
        return {
            "kind": "warm_start",
            "policy_sha256": policy_sha256,
            "training_manifest_sha256": None,
        }

    if arm not in contract["development_panel"]["arms"]:
        raise ValueError("arm is not in the frozen development panel")
    if checkpoint_step not in training["checkpoint_updates"]:
        raise ValueError("checkpoint step is not in the frozen contract")
    if training_manifest is None:
        raise ValueError("trained checkpoints require a training manifest")

    manifest = read_manifest(training_manifest)
    checks = manifest.get("checks")
    if (
        manifest.get("study") != contract["study"]
        or manifest.get("contract") != contract["contract"]
        or manifest.get("status") != "complete"
        or manifest.get("arm") != arm
        or manifest.get("seed") != training_seed
        or manifest.get("final_step") != training["maximum_updates"]
        or not isinstance(checks, dict)
        or not checks
        or not all(checks.values())
    ):
        raise ValueError("training manifest differs from the frozen policy identity")
    artifacts = manifest.get("artifact_sha256", {})
    if artifacts.get("contract") != sha256_file(contract_path):
        raise ValueError("training manifest binds a different contract")
    expected_policy = artifacts.get("required_checkpoints", {}).get(str(checkpoint_step))
    if expected_policy != policy_sha256:
        raise ValueError("policy checkpoint hash differs from the training manifest")
    return {
        "kind": "trained_checkpoint",
        "policy_sha256": policy_sha256,
        "training_manifest_sha256": sha256_file(training_manifest),
    }


def sample_policy(
    *,
    contract_path: Path,
    policy: Path,
    env_dir: Path,
    output: Path,
    manifest_output: Path,
    arm: str,
    training_seed: int,
    checkpoint_step: int,
    training_manifest: Path | None,
    device: str,
    batch_size: int,
) -> dict[str, Any]:
    from rxnflow.sampler import RxnFlowSampler

    if contract_path.resolve() != DEFAULT_CONTRACT.resolve():
        raise ValueError("claim-bearing samples require the released matched contract")
    if output.exists() or manifest_output.exists():
        raise FileExistsError("endpoint sample output already exists")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    identity = validate_policy(
        contract=contract,
        contract_path=contract_path,
        policy=policy,
        arm=arm,
        training_seed=training_seed,
        checkpoint_step=checkpoint_step,
        training_manifest=training_manifest,
    )
    attempts = int(contract["evaluation"]["attempts_per_policy_seed_checkpoint"])
    evaluation_seed = int(contract["evaluation"]["seeds"][str(training_seed)][str(checkpoint_step)])
    sampler = RxnFlowSampler(policy, device=device, env_dir=env_dir)
    results = sampler.sample(attempts, batch_size=batch_size, seed=evaluation_seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(output.suffix + ".tmp")
    sampler.write(results, temporary_output, output_format="jsonl")
    temporary_output.replace(output)
    report = {
        "schema_version": "1.0",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "complete",
        "claim_boundary": (
            "This record fixes one policy sample under the matched evaluation contract. "
            "Target docking and qualifying-hit outcomes remain unopened."
        ),
        "arm": arm,
        "training_seed": training_seed,
        "checkpoint_step": checkpoint_step,
        "evaluation_seed": evaluation_seed,
        "attempts": attempts,
        "returned_valid_trajectories": len(results),
        "invalid_trajectories": attempts - len(results),
        "device": device,
        "batch_size": batch_size,
        "identity": identity,
        "artifact_sha256": {
            "contract": sha256_file(contract_path),
            "sampler": sha256_file(Path(__file__)),
            "samples": sha256_file(output),
        },
        "environment_content_sha256": sampler.env.signature["content_sha256"],
    }
    temporary_manifest = manifest_output.with_suffix(manifest_output.suffix + ".tmp")
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    temporary_manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary_manifest.replace(manifest_output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--training-manifest", type=Path)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--checkpoint-step", type=int, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest-output", type=Path, required=True)
    args = parser.parse_args()
    result = sample_policy(
        contract_path=args.contract,
        policy=args.policy,
        env_dir=args.env_dir,
        output=args.output,
        manifest_output=args.manifest_output,
        arm=args.arm,
        training_seed=args.training_seed,
        checkpoint_step=args.checkpoint_step,
        training_manifest=args.training_manifest,
        device=args.device,
        batch_size=args.batch_size,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
