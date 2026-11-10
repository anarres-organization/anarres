#!/usr/bin/env python3
"""Run one reduced RxnFlow update with a frozen materialized replay bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from materialize_replay_bank import load_into_fresh_replay
from warm_start_weights import load_weights


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_smoke(config_path: Path, env_dir: Path, *, num_online: int, num_replay: int) -> Any:
    if num_online < 1 or num_replay < 1:
        raise ValueError("smoke batch sizes must be positive")
    from rxnflow.config import Config

    config = Config.from_file(config_path)
    config.env_dir = str(env_dir)
    config.training.log_every = 1
    config.training.checkpoint_every = 1
    config.training.num_online = num_online
    config.training.num_replay = num_replay
    config.training.replay_capacity = 512
    config.training.num_replay_insert = 0
    return config


def run_smoke(
    *,
    config_path: Path,
    env_dir: Path,
    warm_start: Path,
    replay_bank: Path,
    prepared_target: Path,
    output_dir: Path,
    report_path: Path,
    seed: int,
    num_online: int,
    num_replay: int,
    device: str,
    retrosynthesis_workers: int,
    reward_workers: int,
) -> dict[str, Any]:
    from rxnflow.trainer import RxnFlowTrainer
    from rxnflow_target_reward import MolecularTargetReward

    config = configure_smoke(config_path, env_dir, num_online=num_online, num_replay=num_replay)
    if retrosynthesis_workers < 0 or reward_workers < 1:
        raise ValueError("smoke worker counts are invalid")
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
    initial = {
        "step": trainer.step,
        "replay_size": len(trainer.replay),
        "optimizer_state_entries": len(trainer.optimizer.state),
    }
    warm_identity = load_weights(trainer, warm_start)
    artifact = json.loads(replay_bank.read_text())
    load_into_fresh_replay(trainer, artifact)
    replay_size_before = len(trainer.replay)
    checkpoint = trainer.run(1)
    record = json.loads((output_dir / "training.jsonl").read_text().strip())
    replay_state = trainer.replay.state_dict()
    replay_size_after = len(replay_state["items"])

    checks = {
        "fresh_step_zero": initial["step"] == 0,
        "fresh_empty_replay": initial["replay_size"] == 0,
        "fresh_empty_optimizer": initial["optimizer_state_entries"] == 0,
        "materialized_bank_complete": replay_size_before == artifact["item_count"],
        "online_insertion_disabled": config.training.num_replay_insert == 0,
        "replay_bank_unchanged": replay_size_after == replay_size_before,
        "one_update_complete": trainer.step == 1,
        "finite_loss": math.isfinite(float(record["loss"])),
        "matched_smoke_batch": record["num_online"] == num_online
        and record["num_replay"] == num_replay,
        "checkpoint_exists": checkpoint.is_file(),
    }
    full_batch = num_online == 64 and num_replay == 64
    report = {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "scope": (
            "full-batch replay-materialization and one-update interface smoke"
            if full_batch
            else "reduced replay-materialization and one-update interface smoke"
        ),
        "status": "pass" if all(checks.values()) else "fail",
        "claim_boundary": (
            "This one-update smoke qualifies the frozen batch and replay-training "
            "interface. It is not a target-training outcome or evidence of bank utility."
            if full_batch
            else "This reduced smoke qualifies the replay-training interface. It is not "
            "a target-training outcome or evidence of bank utility."
        ),
        "seed": seed,
        "bank": artifact["bank"],
        "bank_item_count": artifact["item_count"],
        "warm_start": warm_identity,
        "smoke_batch": {
            "online": num_online,
            "replay": num_replay,
            "updates": 1,
        },
        "observed": {
            "loss": record["loss"],
            "policy_grad_norm": record["policy_grad_norm"],
            "replay_size_before": replay_size_before,
            "replay_size_after": replay_size_after,
        },
        "checks": checks,
        "artifact_sha256": {
            "warm_start": sha256_file(warm_start),
            "replay_bank": sha256_file(replay_bank),
            "checkpoint": sha256_file(checkpoint),
        },
    }
    if full_batch or device != "cpu" or retrosynthesis_workers != 0 or reward_workers != 2:
        report["execution"] = {
            "device": device,
            "retrosynthesis_workers": retrosynthesis_workers,
            "reward_workers": reward_workers,
        }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(report_path)
    if report["status"] != "pass":
        raise RuntimeError("replay-training smoke failed")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--warm-start", type=Path, required=True)
    parser.add_argument("--replay-bank", type=Path, required=True)
    parser.add_argument("--prepared-target", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--num-online", type=int, default=2)
    parser.add_argument("--num-replay", type=int, default=2)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--retrosynthesis-workers", type=int, default=0)
    parser.add_argument("--reward-workers", type=int, default=2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = run_smoke(
        config_path=args.config,
        env_dir=args.env_dir,
        warm_start=args.warm_start,
        replay_bank=args.replay_bank,
        prepared_target=args.prepared_target,
        output_dir=args.output_dir,
        report_path=args.report,
        seed=args.seed,
        num_online=args.num_online,
        num_replay=args.num_replay,
        device=args.device,
        retrosynthesis_workers=args.retrosynthesis_workers,
        reward_workers=args.reward_workers,
    )
    print(f"replay-training smoke {report['status']}: loss={report['observed']['loss']:.6f}")


if __name__ == "__main__":
    main()
