#!/usr/bin/env python3
"""Verify the frozen Q07820 matched training and evaluation contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_path(reference: dict[str, Any]) -> Path:
    prefix = "repo://experiments/ai-for-science/molecular-design/reaction-environment-selection/"
    uri = reference.get("uri", "")
    if not uri.startswith(prefix):
        raise ValueError("matched-contract input is not a study-local repository artifact")
    return ROOT / uri.removeprefix(prefix)


def expected_evaluation_seed(training_seed: int, checkpoint: int) -> int:
    payload = f"q07820-matched-evaluation-v1|{training_seed}|{checkpoint}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**31)


def verify() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("contract") != "q07820-matched-training-evaluation-v1":
        raise ValueError("unexpected matched training contract")

    for name, reference in contract["inputs"].items():
        path = artifact_path(reference)
        if not path.is_file():
            raise ValueError(f"matched-contract input is missing: {name}")
        if sha256_file(path) != reference["sha256"]:
            raise ValueError(f"matched-contract input hash differs: {name}")
        if path.stat().st_size != reference["size_bytes"]:
            raise ValueError(f"matched-contract input size differs: {name}")

    training = contract["training"]
    computed_budgets = [
        update * training["online_trajectories_per_update"]
        for update in training["checkpoint_updates"]
    ]
    if computed_budgets != training["target_oracle_attempt_budgets"]:
        raise ValueError("target-oracle budgets do not match update checkpoints")

    evaluation = contract["evaluation"]
    for training_seed in training["seeds"]:
        for checkpoint in evaluation["checkpoints"]:
            observed = evaluation["seeds"][str(training_seed)][str(checkpoint)]
            if observed != expected_evaluation_seed(training_seed, checkpoint):
                raise ValueError("evaluation seed differs from the frozen derivation")

    bank_result = json.loads((ROOT / "DEVELOPMENT_BANK_QUALIFICATION_V4.json").read_text())
    endpoint_result = json.loads(
        (ROOT / "STARTING_POLICY_ENDPOINT_QUALIFICATION_RESULT_V2.json").read_text()
    )
    replay_smoke = json.loads((ROOT / "REPLAY_TRAINING_SMOKE_V1.json").read_text())
    if bank_result.get("qualification") != "pass":
        raise ValueError("development bank qualification did not pass")
    if bank_result.get("bank_size") != contract["development_panel"]["bank_size"]:
        raise ValueError("development bank size differs from the matched contract")
    if endpoint_result.get("authorizes_matched_training") is not True:
        raise ValueError("starting-policy endpoint does not authorize matched training")
    if replay_smoke.get("status") != "pass":
        raise ValueError("replay training smoke did not pass")

    authorization = contract["authorization"]
    if not all(
        authorization[name]
        for name in (
            "bank_confirmation_passed",
            "starting_policy_endpoint_passed",
            "replay_interface_passed",
            "development_training_authorized",
        )
    ):
        raise ValueError("matched training is not fully authorized")
    if (
        authorization["development_training_started"]
        or authorization["development_or_prospective_outcomes_opened"]
    ):
        raise ValueError("matched contract crosses the sealed outcome boundary")

    return {
        "schema_version": "1.0",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "verified",
        "contract_sha256": sha256_file(CONTRACT),
        "development_arms": len(contract["development_panel"]["arms"]),
        "training_seeds": len(training["seeds"]),
        "maximum_target_oracle_attempts": training["target_oracle_attempt_budgets"][-1],
        "evaluation_attempts_per_policy_seed_checkpoint": evaluation[
            "attempts_per_policy_seed_checkpoint"
        ],
        "development_or_prospective_outcomes_opened": False,
    }


def main() -> None:
    print(json.dumps(verify(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
