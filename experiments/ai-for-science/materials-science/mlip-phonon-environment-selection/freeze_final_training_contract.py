#!/usr/bin/env python3
"""Freeze the claim-bearing MLIP training contract after qualification."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(
    panel_path: Path,
    roles_path: Path,
    qualification_protocol_path: Path,
    qualification_result_path: Path,
    starting_targets_path: Path,
    patch_path: Path,
    config_generator_path: Path,
) -> dict:
    panel = json.loads(panel_path.read_text(encoding="utf-8"))
    protocol = json.loads(qualification_protocol_path.read_text(encoding="utf-8"))
    result = json.loads(qualification_result_path.read_text(encoding="utf-8"))
    targets = json.loads(starting_targets_path.read_text(encoding="utf-8"))
    if result["protocol_sha256"] != sha256(qualification_protocol_path):
        raise ValueError("qualification result does not bind its protocol")
    if result["status"] != "complete_before_final_candidate_training":
        raise ValueError("training qualification is incomplete")
    if targets["status"] != "complete_before_candidate_training":
        raise ValueError("starting-checkpoint target features are incomplete")
    if targets["target_roles_sha256"] != sha256(roles_path):
        raise ValueError("starting-checkpoint features do not bind the target roles")
    selected_rate = result["selected_learning_rate"]
    if selected_rate not in protocol["qualification_grid"]["learning_rates"]:
        raise ValueError("selected learning rate was not prespecified")
    development = [
        {
            "candidate_id": candidate["candidate_id"],
            "membership_sha256": candidate["membership_sha256"],
        }
        for candidate in panel["candidates"]
        if candidate["role"] == "development"
    ]
    prospective = [
        {
            "candidate_id": candidate["candidate_id"],
            "membership_sha256": candidate["membership_sha256"],
        }
        for candidate in panel["candidates"]
        if candidate["role"] == "prospective"
    ]
    if len(development) != 12 or len(prospective) != 4:
        raise ValueError("frozen panel does not contain the expected 12/4 split")
    return {
        "artifact": "anarres_mlip_final_training_contract_v1",
        "status": "frozen_before_final_candidate_training",
        "inputs": {
            "candidate_panel_sha256": sha256(panel_path),
            "target_roles_sha256": sha256(roles_path),
            "starting_checkpoint_targets_sha256": sha256(starting_targets_path),
            "training_qualification_protocol_sha256": sha256(qualification_protocol_path),
            "training_qualification_result_sha256": sha256(qualification_result_path),
            "nequix_patch_sha256": sha256(patch_path),
            "config_generator_sha256": sha256(config_generator_path),
        },
        "starting_checkpoint": protocol["starting_checkpoint"],
        "environment_budget": {
            "atoms_per_pass": 50000,
            "neighbor_edges_per_pass": 2100000,
            "passes": 4,
            "checkpoints_after_passes": [1, 2, 3, 4],
        },
        "optimization": {
            "optimizer": "adamw",
            "learning_rate": selected_rate,
            "weight_decay": 0.001,
            "warmup_epochs": 0.1,
            "warmup_factor": 0.2,
            "gradient_clip_norm": 100.0,
            "batch_size": 64,
            "ema_decay": 0.999,
            "energy_weight": 0.0,
            "force_weight": 20.0,
            "stress_weight": 5.0,
            "loss_type": "mae",
            "precision": "upstream Nequix v0.4.5 defaults",
        },
        "randomization": {
            "training_seeds": [0, 1],
            "validation_fraction": 0.05,
            "validation_seed": 42,
            "python_hash_seed": 0,
        },
        "environments": {
            "development": development,
            "prospective": prospective,
        },
        "execution": {
            "upstream_repository": protocol["implementation"]["upstream_repository"],
            "upstream_commit": protocol["implementation"]["upstream_commit"],
            "upstream_version": protocol["implementation"]["upstream_version"],
            "layout": "one visible B200 per trajectory",
            "checkpoint_contents": "EMA model plus resumable optimizer state",
            "failure_policy": (
                "Retry infrastructure failures with the identical task. Retain scientific "
                "failures and never replace a seed from outcome information."
            ),
        },
        "evaluation_sequence": [
            "train and score every development environment under both seeds",
            (
                "fit and select aggregate-utility and target-regression predictors using only "
                "development outcomes"
            ),
            (
                "serialize predictions, uncertainty, rankings, and artifact hashes for all "
                "prospective environments"
            ),
            "only then train and score the prospective environments",
        ],
        "outcome_boundary": {
            "development_candidate_training_outcomes_used": False,
            "prospective_candidate_training_outcomes_used": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--target-roles", type=Path, required=True)
    parser.add_argument("--qualification-protocol", type=Path, required=True)
    parser.add_argument("--qualification-result", type=Path, required=True)
    parser.add_argument("--starting-targets", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--config-generator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = freeze(
        args.panel,
        args.target_roles,
        args.qualification_protocol,
        args.qualification_result,
        args.starting_targets,
        args.patch,
        args.config_generator,
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
