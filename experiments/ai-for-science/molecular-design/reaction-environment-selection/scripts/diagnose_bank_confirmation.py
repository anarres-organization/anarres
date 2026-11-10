#!/usr/bin/env python3
"""Diagnose a failed two-view bank confirmation without opening training outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from construct_development_banks import construct, eligible_records, normalized_representation
from qualify_development_banks import spearman, summarize_bank


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def standard_error(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(np.std(values, ddof=1) / math.sqrt(len(values)))


def generic_scaffold(scaffold: str) -> str:
    if not scaffold:
        return "__ACYCLIC__"
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold

    molecule = Chem.MolFromSmiles(scaffold)
    if molecule is None:
        raise ValueError(f"invalid stored scaffold: {scaffold}")
    generic = MurckoScaffold.MakeScaffoldGeneric(molecule)
    return Chem.MolToSmiles(generic, canonical=True)


def diagnostic_summary(
    members: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    representation: np.ndarray,
) -> dict[str, Any]:
    result = summarize_bank(members, pool, representation)
    actions = [float(row["generated_action_count"]) for row in members]
    oracle = [float(row["oracle_elapsed_seconds"]) for row in members]
    oracle_per_heavy_atom = [
        float(row["oracle_elapsed_seconds"]) / float(row["heavy_atoms"]) for row in members
    ]
    generic_scaffolds = {generic_scaffold(str(row["bemis_murcko_scaffold"])) for row in members}
    result.update(
        {
            "generated_action_count_standard_error": standard_error(actions),
            "generated_action_count_distribution": {
                str(key): value for key, value in sorted(Counter(actions).items())
            },
            "oracle_seconds_standard_error": standard_error(oracle),
            "median_oracle_seconds": float(np.median(oracle)),
            "mean_oracle_seconds_per_heavy_atom": float(np.mean(oracle_per_heavy_atom)),
            "generic_scaffold_fraction": len(generic_scaffolds) / len(members),
        }
    )
    return result


def targeted_checks(summaries: dict[str, dict[str, Any]]) -> dict[str, bool]:
    baseline = summaries["hash_uniform"]
    return {
        "reward_signal_has_higher_target_reward": (
            summaries["reward_signal"]["mean_target_reward"] > baseline["mean_target_reward"]
        ),
        "validity_cost_has_lower_generated_action_count": (
            summaries["validity_cost"]["mean_generated_action_count"]
            < baseline["mean_generated_action_count"]
        ),
        "validity_cost_has_lower_oracle_seconds": (
            summaries["validity_cost"]["mean_oracle_seconds"] < baseline["mean_oracle_seconds"]
        ),
        "scaffold_coverage_has_at_least_as_many_exact_scaffolds": (
            summaries["scaffold_coverage"]["unique_scaffold_fraction"]
            >= baseline["unique_scaffold_fraction"]
        ),
        "scaffold_coverage_has_more_ring_systems": (
            summaries["scaffold_coverage"]["unique_ring_systems_per_record"]
            > baseline["unique_ring_systems_per_record"]
        ),
        "route_coverage_has_more_routes": (
            summaries["route_coverage"]["unique_route_fraction"] > baseline["unique_route_fraction"]
        ),
        "route_coverage_has_more_reaction_families": (
            summaries["route_coverage"]["unique_reaction_families"]
            > baseline["unique_reaction_families"]
        ),
        "graph_coverage_has_greater_embedding_separation": (
            summaries["graph_embedding_coverage"]["embedding_mean_nearest_neighbor_distance"]
            > baseline["embedding_mean_nearest_neighbor_distance"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, action="append", required=True)
    parser.add_argument("--bank-size", type=int, default=512)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.records) != 2:
        raise ValueError("supply exactly two independent pre-training record files")

    records_by_view = [read_jsonl(path) for path in args.records]
    names = [
        "hash_uniform",
        "reward_signal",
        "validity_cost",
        "scaffold_coverage",
        "route_coverage",
        "graph_embedding_coverage",
    ]
    summaries = []
    checks = []
    for records in records_by_view:
        pool = eligible_records(records)
        banks = construct(records, args.bank_size)
        representation = normalized_representation(pool)
        view_summary = {
            name: diagnostic_summary(banks[name], pool, representation) for name in names
        }
        summaries.append(view_summary)
        checks.append(targeted_checks(view_summary))

    diagnostic_coordinates = [
        "mean_generated_action_count",
        "median_oracle_seconds",
        "mean_oracle_seconds_per_heavy_atom",
        "generic_scaffold_fraction",
    ]
    correlations = {}
    for coordinate in diagnostic_coordinates:
        value, status = spearman(
            [summaries[0][name][coordinate] for name in names],
            [summaries[1][name][coordinate] for name in names],
        )
        correlations[coordinate] = {"spearman": value, "status": status}

    original_failed_coordinates = [
        "mean_generated_action_count",
        "mean_oracle_seconds",
        "unique_scaffold_fraction",
    ]
    original_correlations = {}
    for coordinate in original_failed_coordinates:
        value, _ = spearman(
            [summaries[0][name][coordinate] for name in names],
            [summaries[1][name][coordinate] for name in names],
        )
        original_correlations[coordinate] = value

    non_cost_banks = [name for name in names if name != "validity_cost"]
    non_cost_action_errors = [
        summaries[view][name]["generated_action_count_standard_error"]
        for view in range(2)
        for name in non_cost_banks
    ]
    result = {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "scope": "retrospective diagnosis of the failed version 3 pre-training bank confirmation",
        "authorizes_training": False,
        "training_outcomes_read": False,
        "input_sha256": {path.name: sha256(path) for path in args.records},
        "view_seeds": [int(records[0]["view_seed"]) for records in records_by_view],
        "failed_full_order_correlations": original_correlations,
        "diagnostic_alternatives": {
            "median_oracle_seconds_spearman": correlations["median_oracle_seconds"]["spearman"],
            "mean_oracle_seconds_per_heavy_atom_spearman": correlations[
                "mean_oracle_seconds_per_heavy_atom"
            ]["spearman"],
            "generic_scaffold_fraction_spearman": correlations["generic_scaffold_fraction"][
                "spearman"
            ],
        },
        "failure_mechanisms": {
            "generated_action_count": {
                "construction_non_cost_bank_mean_range": [
                    min(
                        summaries[0][name]["mean_generated_action_count"] for name in non_cost_banks
                    ),
                    max(
                        summaries[0][name]["mean_generated_action_count"] for name in non_cost_banks
                    ),
                ],
                "confirmation_non_cost_bank_mean_range": [
                    min(
                        summaries[1][name]["mean_generated_action_count"] for name in non_cost_banks
                    ),
                    max(
                        summaries[1][name]["mean_generated_action_count"] for name in non_cost_banks
                    ),
                ],
                "non_cost_bank_standard_error_range": [
                    min(non_cost_action_errors),
                    max(non_cost_action_errors),
                ],
                "validity_cost_means": [
                    summaries[view]["validity_cost"]["mean_generated_action_count"]
                    for view in range(2)
                ],
                "interpretation": (
                    "The intended low-cost contrast is exact in both views, while "
                    "incidental ordering among the other five banks is weak."
                ),
            },
            "oracle_seconds": {
                "hash_uniform_means": [
                    summaries[view]["hash_uniform"]["mean_oracle_seconds"] for view in range(2)
                ],
                "validity_cost_means": [
                    summaries[view]["validity_cost"]["mean_oracle_seconds"] for view in range(2)
                ],
                "interpretation": (
                    "The intended low-cost contrast replicates, but changing to a "
                    "median or normalizing by heavy atoms does not stabilize the "
                    "complete six-bank ordering."
                ),
            },
            "scaffold_coverage": {
                "hash_uniform_exact_fraction": [
                    summaries[view]["hash_uniform"]["unique_scaffold_fraction"] for view in range(2)
                ],
                "scaffold_bank_exact_fraction": [
                    summaries[view]["scaffold_coverage"]["unique_scaffold_fraction"]
                    for view in range(2)
                ],
                "hash_uniform_generic_fraction": [
                    summaries[view]["hash_uniform"]["generic_scaffold_fraction"]
                    for view in range(2)
                ],
                "scaffold_bank_generic_fraction": [
                    summaries[view]["scaffold_coverage"]["generic_scaffold_fraction"]
                    for view in range(2)
                ],
                "interpretation": (
                    "The scaffold intervention is higher than the neutral bank in "
                    "both views, while exact uniqueness is nearly saturated and "
                    "genericization does not recover the full ordering."
                ),
            },
        },
        "targeted_selector_checks": {
            "construction_view_all_pass": all(checks[0].values()),
            "confirmation_view_all_pass": all(checks[1].values()),
            "check_count_per_view": len(checks[0]),
        },
        "conclusion": (
            "The version 3 gate tested incidental six-bank orderings beyond the "
            "intended interventions. A new untouched view is required before a "
            "selector-fidelity gate can authorize training."
        ),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "authorizes_training": False}))


if __name__ == "__main__":
    main()
