#!/usr/bin/env python3
"""Normalize released Rubisco active-learning curves and test a frozen direction."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROUNDS_SHA256 = "2509404b378b4a90dcd06c9b51eea9dba39a250e3fc0ce890d57aec0cc9df2bd"
CONFIG_SHA256 = "7d158d9322d997019b051ce07f587544494a949a0ec7594f810dd6b293022758"
DATASETS = ("DMS", "HOFF")
STRATEGIES = ("greedy", "random", "thompson", "ucb", "uncertainty")
REPLICATES = tuple(range(10))
RESAMPLES = 20_000
RANDOM_SEED = 20261112


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def curve_auc(rows: list[dict[str, Any]], outcome: str, common_end: int) -> float:
    selected = sorted(
        (row for row in rows if row["n_assayed"] <= common_end),
        key=lambda row: row["n_assayed"],
    )
    if selected[0]["n_assayed"] != 200 or selected[-1]["n_assayed"] != common_end:
        raise ValueError("curve does not span the common budget")
    area = sum(
        (left[outcome] + right[outcome]) * (right["n_assayed"] - left["n_assayed"]) / 2
        for left, right in zip(selected, selected[1:], strict=False)
    )
    return area / (common_end - 200)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds-csv", type=Path, required=True)
    parser.add_argument("--config-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha256(args.rounds_csv) != ROUNDS_SHA256:
        raise SystemExit("Rubisco active-learning rounds digest mismatch")
    if sha256(args.config_json) != CONFIG_SHA256:
        raise SystemExit("Rubisco active-learning config digest mismatch")
    config = json.loads(args.config_json.read_text())
    if config["strategies"] != ["random", "greedy", "uncertainty", "ucb", "thompson"]:
        raise ValueError("unexpected strategy contract")
    if config["simcfg"]["init_n"] != 200 or config["simcfg"]["batch_size"] != 48:
        raise ValueError("unexpected acquisition budget contract")

    rows = []
    with args.rounds_csv.open(newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    "dataset": raw["dataset"],
                    "strategy": raw["strategy"],
                    "replicate": int(raw["rep"]),
                    "round": int(raw["round"]),
                    "n_assayed": int(raw["n_assayed"]),
                    "recovery_top_1pct": float(raw["recovery_top_1pct"]),
                    "recovery_top_5pct": float(raw["recovery_top_5pct"]),
                }
            )
    if len(rows) != 2_578:
        raise ValueError(f"expected 2,578 released rows, found {len(rows)}")
    if tuple(sorted({row["dataset"] for row in rows})) != DATASETS:
        raise ValueError("unexpected dataset support")
    if tuple(sorted({row["strategy"] for row in rows})) != STRATEGIES:
        raise ValueError("unexpected strategy support")

    runs: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        runs[(row["dataset"], row["strategy"], row["replicate"])].append(row)
    if len(runs) != 100:
        raise ValueError("expected 100 complete strategy replicates")
    for dataset in DATASETS:
        for strategy in STRATEGIES:
            observed = sorted(
                replicate
                for candidate_dataset, candidate_strategy, replicate in runs
                if candidate_dataset == dataset and candidate_strategy == strategy
            )
            if observed != list(REPLICATES):
                raise ValueError(f"incomplete replicate support for {dataset}/{strategy}")

    common_end_by_dataset = {
        dataset: min(
            max(row["n_assayed"] for row in run)
            for (candidate_dataset, _strategy, _replicate), run in runs.items()
            if candidate_dataset == dataset
        )
        for dataset in DATASETS
    }
    run_records = []
    for (dataset, strategy, replicate), run in sorted(runs.items()):
        common_end = common_end_by_dataset[dataset]
        run_records.append(
            {
                "dataset": dataset,
                "strategy": strategy,
                "replicate": replicate,
                "common_budget_start": 200,
                "common_budget_end": common_end,
                "curve_auc_recovery_top_1pct": curve_auc(run, "recovery_top_1pct", common_end),
                "curve_auc_recovery_top_5pct": curve_auc(run, "recovery_top_5pct", common_end),
            }
        )

    summaries = []
    by_dataset_strategy: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in run_records:
        by_dataset_strategy[(row["dataset"], row["strategy"])].append(row)
    for (dataset, strategy), values in sorted(by_dataset_strategy.items()):
        summaries.append(
            {
                "dataset": dataset,
                "strategy": strategy,
                "replicates": len(values),
                "common_budget_end": common_end_by_dataset[dataset],
                "curve_auc_recovery_top_1pct_mean": mean(
                    row["curve_auc_recovery_top_1pct"] for row in values
                ),
                "curve_auc_recovery_top_5pct_mean": mean(
                    row["curve_auc_recovery_top_5pct"] for row in values
                ),
            }
        )

    directional = []
    rng = random.Random(RANDOM_SEED)
    for dataset in DATASETS:
        ucb = {
            row["replicate"]: row["curve_auc_recovery_top_5pct"]
            for row in by_dataset_strategy[(dataset, "ucb")]
        }
        random_values = {
            row["replicate"]: row["curve_auc_recovery_top_5pct"]
            for row in by_dataset_strategy[(dataset, "random")]
        }
        differences = [ucb[replicate] - random_values[replicate] for replicate in REPLICATES]
        bootstrap = [mean(rng.choices(differences, k=len(differences))) for _ in range(RESAMPLES)]
        directional.append(
            {
                "dataset": dataset,
                "common_budget_end": common_end_by_dataset[dataset],
                "ucb_curve_auc_recovery_top_5pct_mean": mean(ucb.values()),
                "random_curve_auc_recovery_top_5pct_mean": mean(random_values.values()),
                "paired_mean_difference": mean(differences),
                "paired_difference_95_interval": [
                    percentile(bootstrap, 0.025),
                    percentile(bootstrap, 0.975),
                ],
                "replicates_with_positive_difference": sum(value > 0 for value in differences),
                "replicates": len(differences),
            }
        )

    output = {
        "schema_version": "anarres.molecular.rubisco_active_learning_bridge.v1",
        "study": (
            "Active Learning on Protein Language Model Embeddings Accelerates Rubisco "
            "Variant Discovery for Desired Traits"
        ),
        "evidence_tier": "retrospective_external_directional_replication",
        "source_revision": "40133a4ba106fa25bd831291809d75c55b5dcc66",
        "source_sha256": {
            "active_learning_rounds.csv": ROUNDS_SHA256,
            "config.json": CONFIG_SHA256,
        },
        "support": {
            "datasets": list(DATASETS),
            "strategies": list(STRATEGIES),
            "replicates_per_strategy_dataset": 10,
            "trajectory_rows": len(rows),
            "complete_runs": len(runs),
            "initial_assays": 200,
            "batch_size": 48,
            "common_budget_end_by_dataset": common_end_by_dataset,
        },
        "directional_contract": {
            "rule_origin": (
                "The separate four-target binding-affinity audit ranks every released "
                "UCB schedule above random acquisition in mean curve utility."
            ),
            "external_question": (
                "Does UCB acquisition also exceed random acquisition on each released "
                "Rubisco curve under a common within-dataset assay budget?"
            ),
            "outcome": "trapezoidal AUC of top-5% recovery over the common assay curve",
            "result": "UCB exceeds random acquisition on both external datasets.",
            "claim_boundary": (
                "This is a retrospective cross-study directional check, not a frozen "
                "multi-arm predictor or a prospective wet-lab result."
            ),
        },
        "directional_results": directional,
        "strategy_summaries": summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
