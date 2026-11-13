#!/usr/bin/env python3
"""Normalize the Explainable AL trajectory release and audit target transfer."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import random
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import mean
from typing import Any

EXPECTED_SHA256 = "2e6b7a7b1df02524423f6c86e0d8f0c51427809ef175daa9185ffe3464e3cddf"
DATASETS = ("D2R", "MPRO", "TYK2", "USP7")
PROTOCOLS = (
    "random",
    "ucb-alternate",
    "ucb-balanced",
    "ucb-exploit-heavy",
    "ucb-explore-heavy",
    "ucb-gradual",
    "ucb-sandwich",
)
KERNELS = ("LinearKernel", "MaternKernel", "RBFKernel", "RQKernel", "TanimotoKernel")
FINGERPRINTS = ("chemberta", "ecfp", "maccs")
SEEDS = (7, 42, 123)
CYCLES = tuple(range(11))
MATCHERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], bool]] = {
    "global_protocol": lambda _candidate, _row: True,
    "kernel_matched": lambda candidate, row: candidate["kernel"] == row["kernel"],
    "fingerprint_matched": lambda candidate, row: candidate["fingerprint"] == row["fingerprint"],
    "matched_configuration": lambda candidate, row: (
        candidate["kernel"] == row["kernel"] and candidate["fingerprint"] == row["fingerprint"]
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    expected_fields = {
        "Dataset",
        "Protocol",
        "Cycle",
        "Recall (2%)",
        "Recall (5%)",
        "Compounds acquired",
        "Kernel",
        "Fingerprint",
        "Seed",
    }
    rows = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != expected_fields:
            raise ValueError("unexpected source columns")
        for raw in reader:
            row = {
                "dataset": raw["Dataset"],
                "protocol": raw["Protocol"],
                "cycle": int(raw["Cycle"]),
                "recall_2pct": float(raw["Recall (2%)"]),
                "recall_5pct": float(raw["Recall (5%)"]),
                "compounds_acquired": int(raw["Compounds acquired"]),
                "kernel": raw["Kernel"],
                "fingerprint": raw["Fingerprint"],
                "seed": int(raw["Seed"]),
            }
            rows.append(row)
    return rows


def validate_support(rows: list[dict[str, Any]]) -> None:
    if len(rows) != 13_860:
        raise ValueError(f"expected 13,860 trajectory rows, found {len(rows)}")
    for field, expected in (
        ("dataset", DATASETS),
        ("protocol", PROTOCOLS),
        ("kernel", KERNELS),
        ("fingerprint", FINGERPRINTS),
        ("seed", SEEDS),
        ("cycle", CYCLES),
    ):
        observed = tuple(sorted({row[field] for row in rows}))
        if observed != tuple(sorted(expected)):
            raise ValueError(f"unexpected {field} support: {observed}")

    runs: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row["dataset"],
            row["protocol"],
            row["kernel"],
            row["fingerprint"],
            row["seed"],
        )
        runs[key].append(row)
    if len(runs) != 1_260:
        raise ValueError(f"expected 1,260 complete runs, found {len(runs)}")
    for key, run in runs.items():
        run.sort(key=lambda row: row["cycle"])
        if [row["cycle"] for row in run] != list(CYCLES):
            raise ValueError(f"incomplete cycle sequence for {key}")
        if [row["compounds_acquired"] for row in run] != [60 + 30 * i for i in CYCLES]:
            raise ValueError(f"unexpected acquisition budget for {key}")


def trapezoidal_curve_auc(run: list[dict[str, Any]], outcome: str) -> float:
    """Average recall over the released 60--360 compound acquisition curve."""
    ordered = sorted(run, key=lambda row: row["compounds_acquired"])
    start = ordered[0]["compounds_acquired"]
    end = ordered[-1]["compounds_acquired"]
    area = sum(
        (left[outcome] + right[outcome])
        * (right["compounds_acquired"] - left["compounds_acquired"])
        / 2
        for left, right in zip(ordered, ordered[1:], strict=False)
    )
    return area / (end - start)


def aggregate_curve(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    runs: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row["dataset"],
            row["fingerprint"],
            row["kernel"],
            row["protocol"],
            row["seed"],
        )
        runs[key].append(row)

    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for (dataset, fingerprint, kernel, protocol, seed), run in sorted(runs.items()):
        grouped[(dataset, fingerprint, kernel, protocol)].append(
            {
                "seed": seed,
                "curve_auc_recall_2pct": trapezoidal_curve_auc(run, "recall_2pct"),
                "curve_auc_recall_5pct": trapezoidal_curve_auc(run, "recall_5pct"),
            }
        )

    records = []
    panels: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for (dataset, fingerprint, kernel, protocol), values in sorted(grouped.items()):
        if sorted(row["seed"] for row in values) != list(SEEDS):
            raise ValueError(
                f"incomplete seed support for {(dataset, fingerprint, kernel, protocol)}"
            )
        record = {
            "dataset": dataset,
            "fingerprint": fingerprint,
            "kernel": kernel,
            "protocol": protocol,
            "acquisition_budget_start": 60,
            "acquisition_budget_end": 360,
            "seeds": len(values),
            "curve_auc_recall_2pct_mean": mean(row["curve_auc_recall_2pct"] for row in values),
            "curve_auc_recall_2pct_by_seed": {
                str(row["seed"]): row["curve_auc_recall_2pct"] for row in values
            },
            "curve_auc_recall_5pct_mean": mean(row["curve_auc_recall_5pct"] for row in values),
        }
        panels[(dataset, fingerprint, kernel)].append(record)

    normalize_panels(records, panels, "curve_auc_recall_2pct_mean")
    return records


def aggregate_endpoint(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    endpoint = [row for row in rows if row["cycle"] == max(CYCLES)]
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in endpoint:
        grouped[(row["dataset"], row["fingerprint"], row["kernel"], row["protocol"])].append(row)

    records = []
    panels: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for (dataset, fingerprint, kernel, protocol), values in sorted(grouped.items()):
        if sorted(row["seed"] for row in values) != list(SEEDS):
            raise ValueError(
                f"incomplete seed support for {(dataset, fingerprint, kernel, protocol)}"
            )
        record = {
            "dataset": dataset,
            "fingerprint": fingerprint,
            "kernel": kernel,
            "protocol": protocol,
            "compounds_acquired": values[0]["compounds_acquired"],
            "seeds": len(values),
            "endpoint_recall_2pct_mean": mean(row["recall_2pct"] for row in values),
            "endpoint_recall_2pct_by_seed": {
                str(row["seed"]): row["recall_2pct"] for row in values
            },
            "endpoint_recall_5pct_mean": mean(row["recall_5pct"] for row in values),
        }
        panels[(dataset, fingerprint, kernel)].append(record)

    normalize_panels(records, panels, "endpoint_recall_2pct_mean")
    return records


def normalize_panels(
    records: list[dict[str, Any]],
    panels: dict[tuple[str, str, str], list[dict[str, Any]]],
    outcome: str,
) -> None:
    for panel, candidates in sorted(panels.items()):
        if sorted(row["protocol"] for row in candidates) != list(PROTOCOLS):
            raise ValueError(f"incomplete candidate set for {panel}")
        low = min(row[outcome] for row in candidates)
        high = max(row[outcome] for row in candidates)
        for row in candidates:
            row["normalized_utility"] = (row[outcome] - low) / (high - low) if high > low else 0.5
            records.append(row)


def aggregate_at_cycle(rows: list[dict[str, Any]], cycle: int) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["cycle"] == cycle]
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        grouped[(row["dataset"], row["fingerprint"], row["kernel"], row["protocol"])].append(row)

    records = []
    panels: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for (dataset, fingerprint, kernel, protocol), values in sorted(grouped.items()):
        record = {
            "dataset": dataset,
            "fingerprint": fingerprint,
            "kernel": kernel,
            "protocol": protocol,
            "compounds_acquired": values[0]["compounds_acquired"],
            "seeds": len(values),
            "recall_2pct_mean": mean(row["recall_2pct"] for row in values),
        }
        panels[(dataset, fingerprint, kernel)].append(record)
    normalize_panels(records, panels, "recall_2pct_mean")
    return records


def score(
    records: list[dict[str, Any]], predictions: dict[tuple[str, str, str, str], float]
) -> dict[str, Any]:
    panels: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        panels[(row["dataset"], row["fingerprint"], row["kernel"])].append(row)

    credits = []
    selections = []
    for (dataset, fingerprint, kernel), candidates in sorted(panels.items()):
        keyed = {
            row["protocol"]: (
                row,
                predictions[(dataset, fingerprint, kernel, row["protocol"])],
            )
            for row in candidates
        }
        for left, right in itertools.combinations(PROTOCOLS, 2):
            observed_delta = (
                keyed[left][0]["normalized_utility"] - keyed[right][0]["normalized_utility"]
            )
            predicted_delta = keyed[left][1] - keyed[right][1]
            credits.append(
                0.5
                if observed_delta == 0 or predicted_delta == 0
                else float(observed_delta * predicted_delta > 0)
            )

        best_prediction = max(value[1] for value in keyed.values())
        selected = sorted(
            protocol for protocol, (_, prediction) in keyed.items() if prediction == best_prediction
        )
        best_observed = max(value[0]["normalized_utility"] for value in keyed.values())
        selected_utility = mean(keyed[protocol][0]["normalized_utility"] for protocol in selected)
        top_credit = mean(
            float(keyed[protocol][0]["normalized_utility"] == best_observed)
            for protocol in selected
        )
        selections.append(
            {
                "dataset": dataset,
                "fingerprint": fingerprint,
                "kernel": kernel,
                "selected_protocols": selected,
                "observed_best_protocols": sorted(
                    protocol
                    for protocol, (row, _) in keyed.items()
                    if row["normalized_utility"] == best_observed
                ),
                "normalized_regret": best_observed - selected_utility,
                "best_protocol_credit": top_credit,
            }
        )
    return {
        "pairwise_ordering": mean(credits),
        "mean_normalized_regret": mean(row["normalized_regret"] for row in selections),
        "best_protocol_credit": mean(row["best_protocol_credit"] for row in selections),
        "panels": len(selections),
        "selections": selections,
    }


def leave_one_dataset_out(
    records: list[dict[str, Any]], matcher: Callable[[dict[str, Any], dict[str, Any]], bool]
) -> dict[str, Any]:
    predictions = {}
    for held_out in DATASETS:
        train = [row for row in records if row["dataset"] != held_out]
        test = [row for row in records if row["dataset"] == held_out]
        for row in test:
            matched = [
                candidate["normalized_utility"]
                for candidate in train
                if candidate["protocol"] == row["protocol"] and matcher(candidate, row)
            ]
            if not matched:
                raise ValueError(f"no training support for {row}")
            key = (row["dataset"], row["fingerprint"], row["kernel"], row["protocol"])
            predictions[key] = mean(matched)
    return score(records, predictions)


def nested_view_selection(records: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = {}
    chosen_views = {}
    for held_out in DATASETS:
        train = [row for row in records if row["dataset"] != held_out]
        test = [row for row in records if row["dataset"] == held_out]
        candidates = []
        for name, matcher in MATCHERS.items():
            inner_predictions = {}
            for validation_dataset in sorted({row["dataset"] for row in train}):
                inner_train = [row for row in train if row["dataset"] != validation_dataset]
                validation = [row for row in train if row["dataset"] == validation_dataset]
                for row in validation:
                    values = [
                        candidate["normalized_utility"]
                        for candidate in inner_train
                        if candidate["protocol"] == row["protocol"] and matcher(candidate, row)
                    ]
                    if not values:
                        raise ValueError(f"no inner training support for {row}")
                    key = (
                        row["dataset"],
                        row["fingerprint"],
                        row["kernel"],
                        row["protocol"],
                    )
                    inner_predictions[key] = mean(values)
            inner = score(train, inner_predictions)
            candidates.append(
                (
                    inner["mean_normalized_regret"],
                    -inner["pairwise_ordering"],
                    name,
                )
            )
        _, _, selected_view = min(candidates)
        chosen_views[held_out] = selected_view
        matcher = MATCHERS[selected_view]
        for row in test:
            values = [
                candidate["normalized_utility"]
                for candidate in train
                if candidate["protocol"] == row["protocol"] and matcher(candidate, row)
            ]
            key = (row["dataset"], row["fingerprint"], row["kernel"], row["protocol"])
            predictions[key] = mean(values)
    result = score(records, predictions)
    result["selection_contract"] = {
        "outer_holdout": "one complete target dataset",
        "inner_holdout": "one complete target dataset from the outer training fold",
        "primary_metric": "mean normalized regret",
        "tie_breaker": "pairwise ordering",
        "candidate_views": list(MATCHERS),
    }
    result["chosen_view_by_held_out_dataset"] = chosen_views
    return result


def fixed_candidate(records: list[dict[str, Any]], selected_protocol: str | None) -> dict[str, Any]:
    predictions = {}
    for row in records:
        key = (row["dataset"], row["fingerprint"], row["kernel"], row["protocol"])
        predictions[key] = (
            0.0 if selected_protocol is None else float(row["protocol"] == selected_protocol)
        )
    return score(records, predictions)


def compact_score(payload: dict[str, Any]) -> dict[str, Any]:
    """Retain aggregate metrics and selection metadata without repeated panel rows."""
    return {key: value for key, value in payload.items() if key != "selections"}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def dataset_bootstrap(
    primary: dict[str, Any], baseline: dict[str, Any], baseline_name: str
) -> dict[str, Any]:
    primary_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    baseline_by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary["selections"]:
        primary_by_dataset[row["dataset"]].append(row)
    for row in baseline["selections"]:
        baseline_by_dataset[row["dataset"]].append(row)

    rng = random.Random(20261112)
    regret_differences = []
    credit_differences = []
    for _ in range(20_000):
        sample = rng.choices(DATASETS, k=len(DATASETS))
        primary_regret = mean(
            mean(row["normalized_regret"] for row in primary_by_dataset[dataset])
            for dataset in sample
        )
        baseline_regret = mean(
            mean(row["normalized_regret"] for row in baseline_by_dataset[dataset])
            for dataset in sample
        )
        primary_credit = mean(
            mean(row["best_protocol_credit"] for row in primary_by_dataset[dataset])
            for dataset in sample
        )
        baseline_credit = mean(
            mean(row["best_protocol_credit"] for row in baseline_by_dataset[dataset])
            for dataset in sample
        )
        regret_differences.append(primary_regret - baseline_regret)
        credit_differences.append(primary_credit - baseline_credit)
    return {
        "independent_datasets": len(DATASETS),
        "resamples": 20_000,
        "random_seed": 20261112,
        "baseline": baseline_name,
        "primary_minus_baseline_regret_95_interval": [
            percentile(regret_differences, 0.025),
            percentile(regret_differences, 0.975),
        ],
        "primary_minus_baseline_best_protocol_credit_95_interval": [
            percentile(credit_differences, 0.025),
            percentile(credit_differences, 0.975),
        ],
        "bootstrap_frequency_primary_lower_regret": mean(
            float(value < 0) for value in regret_differences
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    digest = sha256(args.source_csv)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"source table digest mismatch: {digest}")
    rows = read_rows(args.source_csv)
    validate_support(rows)
    curve_records = aggregate_curve(rows)
    endpoint_records = aggregate_endpoint(rows)

    curve_audits = {
        name: leave_one_dataset_out(curve_records, matcher) for name, matcher in MATCHERS.items()
    }
    curve_nested = nested_view_selection(curve_records)
    endpoint_audits = {
        name: leave_one_dataset_out(endpoint_records, matcher) for name, matcher in MATCHERS.items()
    }
    endpoint_nested = nested_view_selection(endpoint_records)
    curve_random = fixed_candidate(curve_records, "random")
    curve_tie = fixed_candidate(curve_records, None)
    budget_sensitivity = []
    for cycle in CYCLES[1:]:
        budget_records = aggregate_at_cycle(rows, cycle)
        budget_sensitivity.append(
            {
                "compounds_acquired": 60 + 30 * cycle,
                "global_protocol": compact_score(
                    leave_one_dataset_out(budget_records, MATCHERS["global_protocol"])
                ),
            }
        )
    output = {
        "schema_version": "anarres.molecular.explainable_active_learning_bridge.v1",
        "study": "Explainable Active Learning Framework for Ligand Binding Affinity Prediction",
        "evidence_tier": "retrospective_leave_one_target_dataset_out_decision_audit",
        "source_sha256": digest,
        "claim_boundary": (
            "The audit transfers acquisition-schedule outcomes across four released simulated "
            "binding-affinity datasets. It is not a prospective wet-lab result or a "
            "pre-training RxnFlow profile result."
        ),
        "support": {
            "datasets": list(DATASETS),
            "protocols": list(PROTOCOLS),
            "kernels": list(KERNELS),
            "fingerprints": list(FINGERPRINTS),
            "seeds": list(SEEDS),
            "cycles": list(CYCLES),
            "trajectory_rows": len(rows),
            "complete_runs": len(rows) // len(CYCLES),
            "decision_panels": len(
                {(r["dataset"], r["fingerprint"], r["kernel"]) for r in curve_records}
            ),
            "condition_records": len(curve_records),
            "curve_start_compounds_acquired": 60,
            "endpoint_compounds_acquired": 360,
        },
        "decision_contract": {
            "panel": "dataset, molecular fingerprint, and Gaussian-process kernel",
            "candidate": "acquisition schedule",
            "outcome": (
                "three-seed mean trapezoidal AUC of top-2% recall over the released "
                "60--360 compound acquisition curve"
            ),
            "holdout": "one complete target dataset",
            "primary_rule": (
                "predict each schedule from its mean curve utility on the other target "
                "datasets without using held-out-target outcomes"
            ),
            "rationale": (
                "Curve AUC measures finite-budget acquisition efficiency across the full "
                "released trajectory and avoids treating a saturated endpoint as the sole target."
            ),
        },
        "leave_one_dataset_out": {
            "primary_global_protocol": curve_audits["global_protocol"],
            "nested_view_selection": curve_nested,
            **curve_audits,
        },
        "baselines": {
            "random_acquisition": curve_random,
            "uninformed_tie": curve_tie,
        },
        "dataset_clustered_uncertainty": dataset_bootstrap(
            curve_audits["global_protocol"], curve_tie, "uninformed_tie"
        ),
        "budget_specific_sensitivity": budget_sensitivity,
        "endpoint_sensitivity": {
            "outcome": "three-seed mean top-2% recall after 360 acquired compounds",
            "leave_one_dataset_out": {
                "nested_view_selection": compact_score(endpoint_nested),
                **{name: compact_score(audit) for name, audit in endpoint_audits.items()},
            },
            "condition_records": endpoint_records,
        },
        "condition_records": curve_records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
