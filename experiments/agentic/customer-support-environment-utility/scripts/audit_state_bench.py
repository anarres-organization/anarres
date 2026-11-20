#!/usr/bin/env python3
"""Audit a pinned STATE-Bench checkout without reading result directories."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

EXPECTED_REVISION = "5644b1838d96bc4483da29642d058ecaa6f80f7f"
EXPECTED_HASHES = {
    "license_sha256": "2e969379b1a7eaeeefe741c576aa64e29099b9629b645e0e938bf2c88e7b5f0b",
    "learning_track_sha256": "f111b5159d8842c4db210c7bbec1201880aace964dc69909d1fb38bd30ce8a0f",
    "split_manifest_sha256": "2988c8c87d426babf0daa3f342c3110caefb63fa0bac97650a38fc2dcfa7291e",
    "evaluation_protocol_sha256": (
        "e4a97cab2b2ed31ec180f671f4b5e5760c00cf30cc56d4cf717481e7a0d29a0c"
    ),
    "task_inventory_sha256": "7fc71041e595250c974af5df4dd0fbe8de71a695b3ecc86f797e2c5fe35f4382",
    "task_environment_inventory_sha256": (
        "316c9b038fb90241d3c5e55c0c069b1bedc4f9452d7f125f1a85f3c766c4a902"
    ),
    "training_trajectory_inventory_sha256": (
        "6b035244e7a94e85604da9223e10f874f3a61c0e5498310a3f0c0249eaf96163"
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_hash(directory: Path) -> tuple[int, str]:
    paths = sorted(directory.glob("*.json"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return len(paths), digest.hexdigest()


def git_revision(checkout: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def tracked_changes(checkout: Path) -> list[str]:
    """Return tracked changes while allowing the installed untracked extension."""
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=checkout,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def audit_checkout(checkout: Path) -> dict:
    checkout = checkout.resolve()
    revision = git_revision(checkout)
    if revision != EXPECTED_REVISION:
        raise ValueError(f"expected STATE-Bench {EXPECTED_REVISION}, found {revision}")
    changes = tracked_changes(checkout)
    if changes:
        raise ValueError(f"STATE-Bench checkout has tracked changes: {changes}")

    paths = {
        "license_sha256": checkout / "LICENSE",
        "learning_track_sha256": checkout / "docs" / "AGENT_LEARNING_TRACK.md",
        "split_manifest_sha256": checkout
        / "state_bench"
        / "domains"
        / "customer_support"
        / "splits"
        / "train_test.json",
        "evaluation_protocol_sha256": checkout
        / "state_bench"
        / "configs"
        / "eval_protocols"
        / "gpt54.json",
    }
    actual_hashes = {name: sha256_file(path) for name, path in paths.items()}

    inventories = {
        "task_inventory_sha256": checkout
        / "state_bench"
        / "domains"
        / "customer_support"
        / "tasks",
        "task_environment_inventory_sha256": checkout
        / "state_bench"
        / "domains"
        / "customer_support"
        / "task_envs",
        "training_trajectory_inventory_sha256": checkout
        / "datasets"
        / "train_task_trajectories"
        / "customer_support",
    }
    inventory_counts = {}
    for name, directory in inventories.items():
        count, digest = inventory_hash(directory)
        actual_hashes[name] = digest
        inventory_counts[name] = count

    mismatches = {
        name: {"expected": EXPECTED_HASHES[name], "actual": actual}
        for name, actual in actual_hashes.items()
        if actual != EXPECTED_HASHES[name]
    }
    if mismatches:
        raise ValueError(f"STATE-Bench source identity mismatch: {mismatches}")

    split = json.loads(paths["split_manifest_sha256"].read_text(encoding="utf-8"))["splits"]
    train_ids = set(split["train"])
    test_ids = set(split["test"])
    trajectory_ids = {
        path.stem for path in inventories["training_trajectory_inventory_sha256"].glob("*.json")
    }
    if train_ids & test_ids:
        raise ValueError("STATE-Bench train and test task identities overlap")
    if trajectory_ids != train_ids:
        raise ValueError("released training trajectories do not match the train split")

    protocol = json.loads(paths["evaluation_protocol_sha256"].read_text(encoding="utf-8"))
    if protocol.get("split") != "test" or protocol.get("split_version") != "train_test":
        raise ValueError("unexpected STATE-Bench evaluation split contract")
    if protocol.get("num_runs") != 5 or "customer_support" not in protocol.get("domains", []):
        raise ValueError("unexpected STATE-Bench run or domain contract")

    return {
        "source_id": "state_bench",
        "revision": revision,
        "domain": "customer_support",
        "active_task_count": inventory_counts["task_inventory_sha256"],
        "task_environment_count": inventory_counts["task_environment_inventory_sha256"],
        "training_trajectory_count": inventory_counts["training_trajectory_inventory_sha256"],
        "train_split_count": len(train_ids),
        "test_split_count": len(test_ids),
        "train_test_overlap": len(train_ids & test_ids),
        "training_trajectories_match_train_split": trajectory_ids == train_ids,
        "official_runs_per_task": protocol["num_runs"],
        "official_model": protocol["official_model"],
        "content_hashes": actual_hashes,
        "model_calls_made": 0,
        "scientific_outcomes_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(audit_checkout(arguments.checkout), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
