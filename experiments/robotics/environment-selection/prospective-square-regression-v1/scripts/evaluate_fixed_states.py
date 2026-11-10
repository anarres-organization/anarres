#!/usr/bin/env python3
"""Evaluate one robot policy on every state in the frozen Square bank."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import h5py
import numpy as np
import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def episode_seed(base: int, state_id: int, replicate: int) -> int:
    payload = f"{base}:{state_id}:{replicate}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big") % (2**31)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--state-bank", type=Path, required=True)
    parser.add_argument("--state-bank-manifest", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    manifest = json.loads(args.state_bank_manifest.read_text(encoding="utf-8"))
    if sha256(args.state_bank) != manifest["state_bank_sha256"]:
        raise ValueError("state bank differs from its frozen manifest")
    with h5py.File(args.state_bank, "r") as bank:
        states = np.asarray(bank["states"][:], dtype=np.float64)
        strata = np.asarray(bank["stratum"][:], dtype=np.int64)
    if len(states) != protocol["state_bank"]["states"]:
        raise ValueError("state count differs from the frozen protocol")

    import robomimic.utils.file_utils as FileUtils

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    policy, checkpoint = FileUtils.policy_from_checkpoint(
        ckpt_path=str(args.agent), device=device, verbose=False
    )
    env, _ = FileUtils.env_from_checkpoint(
        ckpt_dict=checkpoint,
        render=False,
        render_offscreen=False,
        verbose=False,
    )
    horizon = int(protocol["state_bank"]["horizon"])
    replicates = int(protocol["state_bank"]["policy_rollout_replicates_per_state"])
    base_seed = int(protocol["state_bank"]["action_seed"])
    records = []
    for state_id, state in enumerate(states):
        for replicate in range(replicates):
            seed = episode_seed(base_seed, state_id, replicate)
            np.random.seed(seed)
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            policy.start_episode()
            env.reset()
            current_model = str(env.get_state()["model"])
            observed_model_hash = hashlib.sha256(current_model.encode()).hexdigest()
            if observed_model_hash != manifest["model_xml_sha256"]:
                raise ValueError("evaluation simulator model differs from the frozen state bank")
            observation = env.reset_to({"states": state, "model": current_model})
            success = False
            exception = None
            steps = 0
            try:
                for step_index in range(1, horizon + 1):
                    steps = step_index
                    action = policy(ob=observation)
                    observation, _, done, _ = env.step(action)
                    success = success or bool(env.is_success()["task"])
                    if done or success:
                        break
            except env.rollout_exceptions as error:
                exception = type(error).__name__
                success = False
            records.append(
                {
                    "state_id": state_id,
                    "stratum": int(strata[state_id]),
                    "replicate": replicate,
                    "action_seed": seed,
                    "success": bool(success),
                    "horizon": steps,
                    "exception": exception,
                }
            )

    result = {
        "schema_version": "anarres.robotics-fixed-state-evaluation.v1",
        "study_id": protocol["study_id"],
        "policy_id": args.policy_id,
        "training_seed": args.training_seed,
        "checkpoint_sha256": sha256(args.agent),
        "state_bank_sha256": sha256(args.state_bank),
        "episodes": len(records),
        "successes": sum(record["success"] for record in records),
        "exceptions": sum(record["exception"] is not None for record in records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "episodes": len(records),
                "successes": result["successes"],
                "exceptions": result["exceptions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
