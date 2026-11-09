#!/usr/bin/env python3
"""Apply the frozen starting-policy gates and select one molecular target."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def hash_rank(target_id: str) -> str:
    payload = f"reaction-environment-selection-v1|{target_id}".encode()
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_view(rows: list[dict[str, Any]], expected_records: int) -> dict[str, Any]:
    complete = len(rows) == expected_records and not any(
        row.get("status") == "infrastructure_failure" for row in rows
    )
    eligible = [row for row in rows if row.get("status") == "ok"]
    rewards = [float(row.get("reward", 0.0)) for row in rows]
    oracle_times = [float(row["oracle_elapsed_seconds"]) for row in eligible]
    return {
        "records": len(rows),
        "complete": complete,
        "eligible_fraction": len(eligible) / expected_records,
        "oracle_completion_fraction": 1.0 if complete else 0.0,
        "positive_reward_fraction": sum(value > 0 for value in rewards) / expected_records,
        "median_reward": float(np.median(rewards)) if rewards else None,
        "rewards": rewards,
        "oracle_times": oracle_times,
    }


def apply_target_gates(
    target_id: str,
    view_rows: list[list[dict[str, Any]]],
    contract: dict[str, Any],
    starting_views: dict[str, Any],
    reference_pass: bool,
) -> dict[str, Any]:
    gates = contract["per_target_gates"]
    expected = int(contract["sampling"]["trajectory_attempts_per_view"])
    views = [summarize_view(rows, expected) for rows in view_rows]
    pooled_rewards = [value for view in views for value in view["rewards"]]
    pooled_times = [value for view in views for value in view["oracle_times"]]
    reward_spread = (
        float(np.quantile(pooled_rewards, 0.9) - np.quantile(pooled_rewards, 0.1))
        if pooled_rewards
        else None
    )
    median_time = float(np.median(pooled_times)) if pooled_times else None
    p95_time = float(np.quantile(pooled_times, 0.95)) if pooled_times else None
    valid_fractions = [
        item["returned_valid"] / item["attempts"] for item in starting_views["views"]
    ]
    unique_fractions = [
        item["unique_smiles"] / item["attempts"] for item in starting_views["views"]
    ]
    checks = {
        "reference_oracle_qualification": reference_pass,
        "returned_valid_fraction": all(
            value >= gates["minimum_returned_valid_fraction_per_view"] for value in valid_fractions
        ),
        "unique_fraction": all(
            value >= gates["minimum_unique_fraction_per_view"] for value in unique_fractions
        ),
        "reward_eligible_fraction": all(
            view["eligible_fraction"] >= gates["minimum_reward_eligible_fraction_per_view"]
            for view in views
        ),
        "oracle_completion_fraction": all(
            view["oracle_completion_fraction"]
            >= gates["minimum_oracle_completion_fraction_per_view"]
            for view in views
        ),
        "positive_reward_fraction": all(
            view["positive_reward_fraction"] >= gates["minimum_positive_reward_fraction_per_view"]
            for view in views
        ),
        "reward_spread": reward_spread is not None
        and reward_spread >= gates["minimum_pooled_reward_p90_minus_p10"],
        "median_reward_repeatability": len(views) == 2
        and all(view["median_reward"] is not None for view in views)
        and abs(views[0]["median_reward"] - views[1]["median_reward"])
        <= gates["maximum_absolute_view_median_reward_difference"],
        "positive_fraction_repeatability": abs(
            views[0]["positive_reward_fraction"] - views[1]["positive_reward_fraction"]
        )
        <= gates["maximum_absolute_view_positive_fraction_difference"],
        "median_oracle_time": median_time is not None
        and median_time <= gates["maximum_median_oracle_seconds"],
        "p95_oracle_time": p95_time is not None and p95_time <= gates["maximum_p95_oracle_seconds"],
    }
    for view in views:
        view.pop("rewards")
        view.pop("oracle_times")
    return {
        "target_id": target_id,
        "hash_rank": hash_rank(target_id),
        "views": views,
        "pooled_reward_p90_minus_p10": reward_spread,
        "median_oracle_seconds": median_time,
        "p95_oracle_seconds": p95_time,
        "checks": checks,
        "qualification": "pass" if all(checks.values()) else "fail",
    }


def select_target(
    results_dir: Path,
    contract: dict[str, Any],
    starting_views: dict[str, Any],
    oracle_qualification: dict[str, Any],
) -> dict[str, Any]:
    reference = {
        row["target_id"]: row["qualification"] == "pass" for row in oracle_qualification["targets"]
    }
    seeds = contract["sampling"]["seeds"]
    targets = []
    for target_id in contract["target_panel"]["targets"]:
        paths = [results_dir / f"{target_id}_view_{seed}.jsonl" for seed in seeds]
        target = apply_target_gates(
            target_id,
            [read_jsonl(path) for path in paths],
            contract,
            starting_views,
            reference.get(target_id, False),
        )
        target["view_score_sha256"] = {
            str(seed): file_sha256(path) for seed, path in zip(seeds, paths, strict=True)
        }
        targets.append(target)
    passing = sorted(
        (target for target in targets if target["qualification"] == "pass"),
        key=lambda target: target["hash_rank"],
    )
    return {
        "schema_version": "1.0",
        "study": contract["study"],
        "scope": "starting-policy target qualification and selection",
        "contract_status": contract["status"],
        "targets": targets,
        "passing_targets_in_hash_order": [target["target_id"] for target in passing],
        "selected_target": passing[0]["target_id"] if passing else None,
        "decision": "select" if passing else "abstain",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--starting-views", type=Path, required=True)
    parser.add_argument("--oracle-qualification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = select_target(
        args.results_dir,
        read_json(args.contract),
        read_json(args.starting_views),
        read_json(args.oracle_qualification),
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps({"decision": result["decision"], "selected_target": result["selected_target"]})
    )


if __name__ == "__main__":
    main()
