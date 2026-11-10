#!/usr/bin/env python3
"""Apply the frozen selected-target measurement reliability gates."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def effective_rank(values: np.ndarray) -> float:
    centered = values - values.mean(axis=0, keepdims=True)
    singular_values = np.linalg.svd(centered, full_matrices=False, compute_uv=False)
    variances = singular_values**2
    total = variances.sum()
    if total <= 0:
        return 0.0
    probabilities = variances[variances > 0] / total
    return float(np.exp(-np.sum(probabilities * np.log(probabilities))))


def js_divergence(first: Counter[str], second: Counter[str]) -> float:
    support = sorted(set(first) | set(second))
    if not support:
        return 0.0
    p = np.asarray([first[key] for key in support], dtype=float)
    q = np.asarray([second[key] for key in support], dtype=float)
    p /= p.sum()
    q /= q.sum()
    midpoint = 0.5 * (p + q)

    def kl(values: np.ndarray) -> float:
        mask = values > 0
        return float(np.sum(values[mask] * np.log(values[mask] / midpoint[mask])))

    return 0.5 * (kl(p) + kl(q))


def cosine(first: np.ndarray, second: np.ndarray) -> float:
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    return float(first @ second / denominator) if denominator > 0 else 0.0


def summarize_view(records: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    attempts = int(manifest["attempts"])
    returned = len(records)
    rewards = np.asarray([float(row["target_reward"] or 0.0) for row in records], dtype=float)
    eligible = [row for row in records if row["reward_status"] == "ok"]
    oracle_times = np.asarray(
        [float(row["oracle_elapsed_seconds"]) for row in eligible], dtype=float
    )
    unique_canonical_products = len({row["canonical_smiles"] for row in records})
    embeddings = np.asarray([row["graph_embedding"] for row in records], dtype=float)
    reaction_counts = Counter(family for row in records for family in row["reaction_sequence"])
    scaffold_counts = Counter(row["bemis_murcko_scaffold"] for row in records)
    return {
        "view_seed": manifest["view_seed"],
        "attempts": attempts,
        "returned_records": returned,
        "returned_valid_fraction": returned / attempts,
        "unique_canonical_products": unique_canonical_products,
        "unique_canonical_smiles_fraction": unique_canonical_products / returned,
        "reward_eligible_fraction": len(eligible) / returned,
        "oracle_completion_fraction": sum(
            row["reward_status"] != "infrastructure_failure" for row in records
        )
        / returned,
        "positive_reward_fraction": float(np.mean(rewards > 0)),
        "median_reward": float(np.median(rewards)),
        "reward_p90_minus_p10": float(np.quantile(rewards, 0.9) - np.quantile(rewards, 0.1)),
        "median_oracle_seconds": float(np.median(oracle_times)),
        "p95_oracle_seconds": float(np.quantile(oracle_times, 0.95)),
        "mean_reaction_depth": float(np.mean([row["reaction_depth"] for row in records])),
        "scaffold_singleton_fraction": sum(value == 1 for value in scaffold_counts.values())
        / returned,
        "graph_embedding_centroid": embeddings.mean(axis=0),
        "graph_embedding_effective_rank": effective_rank(embeddings),
        "reaction_family_counts": reaction_counts,
        "finite_graph_embeddings": bool(np.isfinite(embeddings).all()),
    }


def qualify(
    contract: dict[str, Any],
    records_by_view: list[list[dict[str, Any]]],
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(records_by_view) != 2 or len(manifests) != 2:
        raise ValueError("the frozen contract requires exactly two views")
    expected_seeds = contract["sampling"]["seeds"]
    observed_seeds = [manifest["view_seed"] for manifest in manifests]
    if observed_seeds != expected_seeds:
        raise ValueError("view seeds do not match the frozen contract")
    for records, manifest in zip(records_by_view, manifests, strict=True):
        if manifest["target_id"] != contract["selected_target"]:
            raise ValueError("target identity does not match the frozen contract")
        if manifest["attempts"] != contract["sampling"]["attempts_per_view"]:
            raise ValueError("attempt count does not match the frozen contract")
        if manifest["returned_records"] != len(records):
            raise ValueError("manifest record count does not match the records file")
        if any(row["target_id"] != manifest["target_id"] for row in records):
            raise ValueError("record target identity does not match its manifest")
    views = [
        summarize_view(records, manifest)
        for records, manifest in zip(records_by_view, manifests, strict=True)
    ]
    per = contract["per_view_gates"]
    per_view_checks = []
    for view in views:
        per_view_checks.append(
            {
                "returned_valid_fraction": view["returned_valid_fraction"]
                >= per["minimum_returned_valid_fraction"],
                "unique_canonical_smiles_fraction": view["unique_canonical_smiles_fraction"]
                >= per["minimum_unique_canonical_smiles_fraction"],
                "unique_canonical_products": view["unique_canonical_products"]
                >= per.get("minimum_unique_canonical_products", 0),
                "reward_eligible_fraction": view["reward_eligible_fraction"]
                >= per["minimum_reward_eligible_fraction"],
                "oracle_completion_fraction": view["oracle_completion_fraction"]
                >= per["minimum_oracle_completion_fraction"],
                "positive_reward_fraction": view["positive_reward_fraction"]
                >= per["minimum_positive_reward_fraction"],
                "reward_spread": view["reward_p90_minus_p10"]
                >= per["minimum_reward_p90_minus_p10"],
                "median_oracle_seconds": view["median_oracle_seconds"]
                <= per["maximum_median_oracle_seconds"],
                "p95_oracle_seconds": view["p95_oracle_seconds"]
                <= per["maximum_p95_oracle_seconds"],
                "finite_graph_embeddings": view["finite_graph_embeddings"],
            }
        )
    two = contract["two_view_gates"]
    first, second = views
    first_rank = first["graph_embedding_effective_rank"]
    second_rank = second["graph_embedding_effective_rank"]
    rank_denominator = max(first_rank, second_rank, np.finfo(float).eps)
    two_view_metrics = {
        "absolute_returned_valid_fraction_difference": abs(
            first["returned_valid_fraction"] - second["returned_valid_fraction"]
        ),
        "absolute_unique_fraction_difference": abs(
            first["unique_canonical_smiles_fraction"] - second["unique_canonical_smiles_fraction"]
        ),
        "absolute_reward_eligible_fraction_difference": abs(
            first["reward_eligible_fraction"] - second["reward_eligible_fraction"]
        ),
        "absolute_positive_reward_fraction_difference": abs(
            first["positive_reward_fraction"] - second["positive_reward_fraction"]
        ),
        "absolute_median_reward_difference": abs(first["median_reward"] - second["median_reward"]),
        "absolute_reward_spread_difference": abs(
            first["reward_p90_minus_p10"] - second["reward_p90_minus_p10"]
        ),
        "absolute_mean_reaction_depth_difference": abs(
            first["mean_reaction_depth"] - second["mean_reaction_depth"]
        ),
        "reaction_family_js_divergence": js_divergence(
            first["reaction_family_counts"], second["reaction_family_counts"]
        ),
        "absolute_scaffold_singleton_fraction_difference": abs(
            first["scaffold_singleton_fraction"] - second["scaffold_singleton_fraction"]
        ),
        "graph_embedding_centroid_cosine_similarity": cosine(
            first["graph_embedding_centroid"], second["graph_embedding_centroid"]
        ),
        "relative_graph_embedding_effective_rank_difference": abs(first_rank - second_rank)
        / rank_denominator,
    }
    two_view_checks = {
        "returned_valid_fraction": two_view_metrics["absolute_returned_valid_fraction_difference"]
        <= two["maximum_absolute_returned_valid_fraction_difference"],
        "unique_fraction": two_view_metrics["absolute_unique_fraction_difference"]
        <= two["maximum_absolute_unique_fraction_difference"],
        "reward_eligible_fraction": two_view_metrics["absolute_reward_eligible_fraction_difference"]
        <= two["maximum_absolute_reward_eligible_fraction_difference"],
        "positive_reward_fraction": two_view_metrics["absolute_positive_reward_fraction_difference"]
        <= two["maximum_absolute_positive_reward_fraction_difference"],
        "median_reward": two_view_metrics["absolute_median_reward_difference"]
        <= two["maximum_absolute_median_reward_difference"],
        "reward_spread": two_view_metrics["absolute_reward_spread_difference"]
        <= two["maximum_absolute_reward_spread_difference"],
        "reaction_depth": two_view_metrics["absolute_mean_reaction_depth_difference"]
        <= two["maximum_absolute_mean_reaction_depth_difference"],
        "reaction_family_distribution": two_view_metrics["reaction_family_js_divergence"]
        <= two["maximum_reaction_family_js_divergence"],
        "scaffold_singleton_fraction": two_view_metrics[
            "absolute_scaffold_singleton_fraction_difference"
        ]
        <= two["maximum_absolute_scaffold_singleton_fraction_difference"],
        "graph_embedding_centroid": two_view_metrics["graph_embedding_centroid_cosine_similarity"]
        >= two["minimum_graph_embedding_centroid_cosine_similarity"],
        "graph_embedding_effective_rank": two_view_metrics[
            "relative_graph_embedding_effective_rank_difference"
        ]
        <= two["maximum_relative_graph_embedding_effective_rank_difference"],
    }
    for view in views:
        view.pop("graph_embedding_centroid")
        view["reaction_family_counts"] = dict(sorted(view["reaction_family_counts"].items()))
    passed = all(all(checks.values()) for checks in per_view_checks) and all(
        two_view_checks.values()
    )
    return {
        "schema_version": "1.0",
        "study": contract["study"],
        "scope": "selected-target measurement reliability",
        "qualification": "pass" if passed else "fail",
        "views": views,
        "per_view_checks": per_view_checks,
        "two_view_metrics": two_view_metrics,
        "two_view_checks": two_view_checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--records", type=Path, action="append", required=True)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.records) != len(args.manifest):
        raise ValueError("supply one manifest for each records file")
    manifests = [read_json(path) for path in args.manifest]
    for records_path, manifest in zip(args.records, manifests, strict=True):
        if file_sha256(records_path) != manifest["output_sha256"]:
            raise ValueError(f"records digest mismatch: {records_path}")
    result = qualify(
        read_json(args.contract),
        [read_jsonl(path) for path in args.records],
        manifests,
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"qualification": result["qualification"]}))


if __name__ == "__main__":
    main()
