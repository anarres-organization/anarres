#!/usr/bin/env python3
"""Run one frozen Q07820 development arm under the matched study contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from materialize_replay_bank import canonical_json_sha256, load_into_fresh_replay
from verify_matched_training_contract import verify as verify_matched_contract
from warm_start_weights import load_weights

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_jsonl(path: Path) -> int:
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def validate_arm_and_seed(contract: dict[str, Any], arm: str, seed: int) -> None:
    if arm not in contract["development_panel"]["arms"]:
        raise ValueError(f"arm is not in the frozen development panel: {arm}")
    if seed not in contract["training"]["seeds"]:
        raise ValueError(f"seed is not in the frozen training set: {seed}")


def validate_replay_artifact(artifact: dict[str, Any], contract: dict[str, Any], arm: str) -> None:
    if artifact.get("bank") != arm:
        raise ValueError("replay artifact identifies a different development arm")
    if artifact.get("item_count") != contract["development_panel"]["bank_size"]:
        raise ValueError("replay artifact has the wrong frozen bank size")
    expected_qualification = contract["inputs"]["bank_qualification"]["sha256"]
    if artifact.get("source", {}).get("qualification_sha256") != expected_qualification:
        raise ValueError("replay artifact is not derived from the frozen qualification")


def configure(config_path: Path, env_dir: Path) -> Any:
    from rxnflow.config import Config

    config = Config.from_file(config_path)
    config.env_dir = str(env_dir)
    return config


def replay_digest(trainer: Any) -> str:
    return canonical_json_sha256(trainer.replay.state_dict()["items"])


def run_training(
    *,
    contract_path: Path,
    config_path: Path,
    env_dir: Path,
    warm_start: Path,
    replay_bank: Path,
    prepared_target: Path,
    output_dir: Path,
    arm: str,
    seed: int,
    device: str,
    retrosynthesis_workers: int,
    reward_workers: int,
    resume_from: Path | None,
) -> dict[str, Any]:
    from rxnflow.trainer import RxnFlowTrainer
    from rxnflow_target_reward import MolecularTargetReward

    if contract_path.resolve() != DEFAULT_CONTRACT.resolve():
        raise ValueError("claim-bearing runs require the released matched contract")
    verification = verify_matched_contract()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    validate_arm_and_seed(contract, arm, seed)

    config_reference = contract["inputs"]["training_config"]
    if sha256_file(config_path) != config_reference["sha256"]:
        raise ValueError("training configuration differs from the frozen contract")
    if sha256_file(warm_start) != contract["starting_policy"]["weights_only_sha256"]:
        raise ValueError("warm-start weights differ from the frozen starting policy")
    artifact = json.loads(replay_bank.read_text(encoding="utf-8"))
    validate_replay_artifact(artifact, contract, arm)
    if reward_workers < 1 or retrosynthesis_workers < 0:
        raise ValueError("worker counts are invalid")

    config = configure(config_path, env_dir)
    training = contract["training"]
    expected_config = {
        "num_online": training["online_trajectories_per_update"],
        "num_replay": training["replay_trajectories_per_update"],
        "replay_capacity": training["replay_capacity"],
        "num_replay_insert": training["replay_insertions_per_update"],
    }
    for key, expected in expected_config.items():
        if getattr(config.training, key) != expected:
            raise ValueError(f"resolved training configuration differs at {key}")

    reward = MolecularTargetReward(
        str(prepared_target), timeout_seconds=300.0, max_workers=reward_workers
    )
    trainer = RxnFlowTrainer(
        config,
        reward,
        seed=seed,
        output_dir=output_dir,
        device=device,
        num_workers=retrosynthesis_workers,
    )
    warm_identity: dict[str, Any] | None = None
    resume_identity: dict[str, Any] | None = None
    if resume_from is None:
        warm_identity = load_weights(trainer, warm_start)
        load_into_fresh_replay(trainer, artifact)
    else:
        trainer.load_checkpoint(resume_from)
        if trainer.seed != seed:
            raise ValueError("resume checkpoint uses a different frozen seed")
        resume_identity = {
            "path_name": resume_from.name,
            "sha256": sha256_file(resume_from),
            "step": trainer.step,
        }

    initial_step = trainer.step
    maximum_updates = training["maximum_updates"]
    if not 0 <= initial_step < maximum_updates:
        raise ValueError("initial step cannot reach or exceed the frozen stopping point")
    replay_size_before = len(trainer.replay)
    replay_digest_before = replay_digest(trainer)
    checkpoint = trainer.run(maximum_updates - initial_step)
    replay_size_after = len(trainer.replay)
    replay_digest_after = replay_digest(trainer)

    log_path = output_dir / "training.jsonl"
    sample_path = output_dir / "sample.jsonl"
    expected_updates = maximum_updates - initial_step
    required_steps = [step for step in training["checkpoint_updates"] if step > initial_step]
    required_checkpoints = {
        str(step): output_dir / "checkpoints" / f"step_{step:06d}.ckpt" for step in required_steps
    }
    checks = {
        "contract_verified": verification["status"] == "verified",
        "completed_frozen_updates": trainer.step == maximum_updates,
        "training_records_complete": count_jsonl(log_path) == expected_updates,
        "online_samples_complete": count_jsonl(sample_path)
        == expected_updates * training["online_trajectories_per_update"],
        "replay_size_preserved": replay_size_before
        == replay_size_after
        == training["replay_capacity"],
        "replay_content_preserved": replay_digest_before == replay_digest_after,
        "required_checkpoints_present": all(
            path.is_file() for path in required_checkpoints.values()
        ),
        "final_checkpoint_matches": checkpoint
        == output_dir / "checkpoints" / f"step_{maximum_updates:06d}.ckpt",
    }
    if not all(checks.values()):
        raise RuntimeError(f"matched training integrity checks failed: {checks}")

    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    final = records[-1]
    if not all(math.isfinite(float(final[key])) for key in ("loss", "reward")):
        raise RuntimeError("final training diagnostics are non-finite")
    manifest = {
        "schema_version": "1.0",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "complete",
        "claim_boundary": (
            "This manifest records one matched development trajectory. Endpoint "
            "evaluation and cross-arm utility scoring remain separate."
        ),
        "arm": arm,
        "seed": seed,
        "initial_step": initial_step,
        "final_step": trainer.step,
        "warm_start": warm_identity,
        "resume": resume_identity,
        "workers": {
            "retrosynthesis": retrosynthesis_workers,
            "reward": reward_workers,
        },
        "replay": {
            "size": replay_size_after,
            "items_sha256": replay_digest_after,
        },
        "final_training_diagnostics": {
            "loss": final["loss"],
            "reward": final["reward"],
            "policy_grad_norm": final["policy_grad_norm"],
            "valid_fraction": final["num_valid"] / final["num_online"],
            "unique_fraction": final["num_unique"] / max(1, final["num_valid"]),
        },
        "checks": checks,
        "artifact_sha256": {
            "contract": sha256_file(contract_path),
            "runner": sha256_file(Path(__file__)),
            "configuration": sha256_file(config_path),
            "warm_start": sha256_file(warm_start),
            "replay_bank": sha256_file(replay_bank),
            "training_log": sha256_file(log_path),
            "online_samples": sha256_file(sample_path),
            "final_checkpoint": sha256_file(checkpoint),
            "required_checkpoints": {
                step: sha256_file(path) for step, path in required_checkpoints.items()
            },
        },
    }
    manifest_path = output_dir / "MATCHED_TRAINING_RUN.json"
    temporary = manifest_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    temporary.replace(manifest_path)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--warm-start", type=Path, required=True)
    parser.add_argument("--replay-bank", type=Path, required=True)
    parser.add_argument("--prepared-target", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--retrosynthesis-workers", type=int, default=4)
    parser.add_argument("--reward-workers", type=int, default=16)
    parser.add_argument("--resume-from", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    manifest = run_training(
        contract_path=args.contract,
        config_path=args.config,
        env_dir=args.env_dir,
        warm_start=args.warm_start,
        replay_bank=args.replay_bank,
        prepared_target=args.prepared_target,
        output_dir=args.output_dir,
        arm=args.arm,
        seed=args.seed,
        device=args.device,
        retrosynthesis_workers=args.retrosynthesis_workers,
        reward_workers=args.reward_workers,
        resume_from=args.resume_from,
    )
    print(
        f"matched training complete: arm={manifest['arm']} seed={manifest['seed']} "
        f"step={manifest['final_step']}"
    )


if __name__ == "__main__":
    main()
