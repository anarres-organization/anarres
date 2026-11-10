#!/usr/bin/env python3
"""Freeze candidate memberships from CUPID scores before policy training."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

CANONICAL_KEY = "sum_of_sum-net-all"
TIERS = ("better", "okay", "worse")


def demo_number(name: str) -> int:
    return int(name.rsplit("_", 1)[1])


def ordinal_ranks(values: list[float], names: list[str]) -> list[int]:
    order = sorted(range(len(values)), key=lambda i: (values[i], demo_number(names[i])))
    ranks = [0] * len(values)
    for rank, index in enumerate(order):
        ranks[index] = rank
    return ranks


def correlation(left: list[int], right: list[int]) -> float:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=True))
    left_scale = math.sqrt(sum((x - left_mean) ** 2 for x in left))
    right_scale = math.sqrt(sum((y - right_mean) ** 2 for y in right))
    return numerator / (left_scale * right_scale)


def top_set(ranks: list[int], names: list[str], count: int) -> set[str]:
    order = sorted(range(len(names)), key=lambda i: (-ranks[i], demo_number(names[i])))
    return {names[i] for i in order[:count]}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def membership_hash(names: list[str]) -> str:
    payload = "\n".join(sorted(names, key=demo_number)) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def build_candidates(
    names: list[str],
    tiers: dict[str, str],
    merged_ranks: list[float],
    baselines: dict[str, list[str]],
    subset_count: int,
    per_tier_count: int,
) -> dict[str, list[str]]:
    if set(names) != set(tiers):
        raise ValueError("tier metadata must cover exactly the scored demonstrations")
    if any(tiers[name] not in TIERS for name in names):
        raise ValueError("unknown operator tier")
    order = sorted(range(len(names)), key=lambda i: (-merged_ranks[i], demo_number(names[i])))
    candidates = {
        "all_data": sorted(names, key=demo_number),
        "random_50": sorted(baselines["random_50"], key=demo_number),
        "length_50": sorted(baselines["length_50"], key=demo_number),
        "cupid_50": sorted((names[i] for i in order[:subset_count]), key=demo_number),
    }
    balanced = []
    for tier in TIERS:
        tier_order = [i for i in order if tiers[names[i]] == tier]
        if len(tier_order) < per_tier_count:
            raise ValueError(f"tier {tier} cannot supply the required candidate count")
        balanced.extend(names[i] for i in tier_order[:per_tier_count])
    candidates["cupid_tier_balanced_50"] = sorted(balanced, key=demo_number)
    expected = {
        "all_data": len(names),
        "random_50": subset_count,
        "length_50": subset_count,
        "cupid_50": subset_count,
        "cupid_tier_balanced_50": per_tier_count * len(TIERS),
    }
    for candidate_id, members in candidates.items():
        if len(members) != expected[candidate_id] or len(members) != len(set(members)):
            raise ValueError(f"invalid membership for {candidate_id}")
        if set(members) - set(names):
            raise ValueError(f"unknown demonstration in {candidate_id}")
    return candidates


def read_score(path: Path) -> dict:
    blob = json.loads(path.read_text())
    if blob.get("canonical_exp_key") != CANONICAL_KEY:
        raise ValueError(f"unexpected CUPID aggregation in {path}")
    values = blob["scores"][CANONICAL_KEY]
    if not values or any(not math.isfinite(float(x)) for x in values):
        raise ValueError(f"nonfinite or empty CUPID scores in {path}")
    outcomes = [int(x) for x in blob["test"]["success"]]
    if set(outcomes) != {0, 1}:
        raise ValueError(f"scoring rollouts must contain successes and failures: {path}")
    return blob


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", nargs=3, type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)

    protocol = json.loads(args.protocol.read_text())
    metadata = json.loads(args.metadata.read_text())
    blobs = [read_score(path) for path in args.scores]
    names = blobs[0]["demos"]
    if any(blob["demos"] != names for blob in blobs[1:]):
        raise ValueError("scoring checkpoints cover different demonstrations")

    ranks = [ordinal_ranks(blob["scores"][CANONICAL_KEY], names) for blob in blobs]
    correlations = [correlation(ranks[i], ranks[j]) for i, j in combinations(range(3), 2)]
    top_sets = [top_set(rank, names, len(names) // 2) for rank in ranks]
    overlaps = [jaccard(top_sets[i], top_sets[j]) for i, j in combinations(range(3), 2)]
    merged = [sum(rank[i] for rank in ranks) / len(ranks) for i in range(len(names))]

    gate = protocol["measurement"]["reliability_gate"]
    mean_correlation = sum(correlations) / len(correlations)
    mean_overlap = sum(overlaps) / len(overlaps)
    gate_passed = (
        mean_correlation >= gate["minimum_mean_pairwise_spearman"]
        and mean_overlap >= gate["minimum_mean_pairwise_top_half_jaccard"]
    )
    candidates = build_candidates(
        names=names,
        tiers=metadata["tiers"],
        merged_ranks=merged,
        baselines=metadata["baselines"],
        subset_count=150,
        per_tier_count=50,
    )
    result = {
        "study_id": protocol["study_id"],
        "status": "CANDIDATES_FROZEN__OUTCOMES_UNOPENED",
        "measurement_reliability": {
            "pairwise_spearman": correlations,
            "mean_pairwise_spearman": mean_correlation,
            "pairwise_top_half_jaccard": overlaps,
            "mean_pairwise_top_half_jaccard": mean_overlap,
            "gate_passed": gate_passed,
        },
        "decision": (
            protocol["decision"]["point_prediction_if_gate_passes"]
            if gate_passed
            else protocol["decision"]["if_gate_fails"]
        ),
        "candidates": {
            key: {
                "count": len(value),
                "members": value,
                "membership_sha256": membership_hash(value),
            }
            for key, value in candidates.items()
        },
        "score_inputs": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.scores
        },
        "outcomes_read": False,
    }
    args.out.mkdir(parents=True)
    output = args.out / "CANDIDATES.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), **result["measurement_reliability"]}, indent=2))


if __name__ == "__main__":
    main()
