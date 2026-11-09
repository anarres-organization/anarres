#!/usr/bin/env python3
"""Open frozen labels only after every candidate prediction is complete, then score."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def load_hashed(path: Path, field: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    stored = payload.pop(field)
    if stored != canonical_digest(payload):
        raise ValueError(f"{path.name} digest does not match its contents")
    payload[field] = stored
    return payload


def local_id(row: dict) -> str:
    return Path(row["id"]).stem


def auc(labels: list[bool], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("AUC requires both classes")
    ordered = sorted(range(len(scores)), key=lambda i: (scores[i], i))
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(ordered):
        stop = start + 1
        while stop < len(ordered) and scores[ordered[stop]] == scores[ordered[start]]:
            stop += 1
        mean_rank = (start + 1 + stop) / 2
        for position in range(start, stop):
            ranks[ordered[position]] = mean_rank
        start = stop
    positive_rank_sum = sum(rank for rank, label in zip(ranks, labels, strict=False) if label)
    return (positive_rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def concordance(targets: list[float], scores: list[float]) -> float:
    correct = total = 0.0
    for left in range(len(scores)):
        for right in range(left + 1, len(scores)):
            target_sign = (targets[left] > targets[right]) - (targets[left] < targets[right])
            score_sign = (scores[left] > scores[right]) - (scores[left] < scores[right])
            if target_sign == 0:
                continue
            total += 1
            correct += 0.5 if score_sign == 0 else float(score_sign == target_sign)
    if total == 0:
        raise ValueError("Continuous concordance has no comparable pairs")
    return correct / total


def evaluate(rows: list[dict], k: int) -> dict:
    labels = [float(row["min_frequency"]) > -0.1 for row in rows]
    targets = [float(row["min_frequency"]) for row in rows]
    composite = [float(row["composite_score"]) for row in rows]
    probabilities = [float(row["threshold_probability_minus_0p1"]) for row in rows]
    predictions = [float(row["prediction"]) for row in rows]
    if not all(0 <= value <= 1 for value in probabilities):
        raise ValueError("Threshold probabilities lie outside [0, 1]")
    order = sorted(range(len(rows)), key=lambda index: (-composite[index], rows[index]["local_id"]))
    return {
        "records": len(rows),
        "stable_records": sum(labels),
        "stable_fraction": sum(labels) / len(labels),
        "top_k": k,
        "top_k_stable_rate": sum(labels[index] for index in order[:k]) / k,
        "continuous_pairwise_concordance": concordance(targets, composite),
        "roc_auc": auc(labels, composite),
        "brier_score": math.fsum(
            (probability - float(label)) ** 2
            for probability, label in zip(probabilities, labels, strict=False)
        )
        / len(labels),
        "minimum_frequency_mae_thz": math.fsum(
            abs(prediction - target)
            for prediction, target in zip(predictions, targets, strict=False)
        )
        / len(targets),
    }


def read_predictions(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def join(labels: list[dict], predictions: list[dict]) -> list[dict]:
    by_id = {row["local_id"]: row for row in predictions}
    label_ids = {local_id(row) for row in labels}
    if len(by_id) != len(predictions) or set(by_id) != label_ids:
        raise ValueError("Prediction and external-label identities do not match one-to-one")
    return [{**label, **by_id[local_id(label)]} for label in labels]


def pairwise_order_accuracy(order: list[str], utilities: dict[str, float]) -> float:
    credit = total = 0.0
    for left in range(len(order)):
        for right in range(left + 1, len(order)):
            total += 1
            difference = utilities[order[left]] - utilities[order[right]]
            credit += 1.0 if difference > 0 else (0.5 if difference == 0 else 0.0)
    return credit / total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--launch-manifest", type=Path, required=True)
    parser.add_argument("--prediction-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    contract = json.loads(args.evaluation_contract.read_text(encoding="utf-8"))
    if sha256(args.archive) != contract["source_archive_sha256"]:
        raise ValueError("Source archive differs from frozen evaluation contract")
    predictions_manifest = load_hashed(
        args.prediction_root / "PREDICTION_MANIFEST.json", "prediction_manifest_sha256"
    )
    if (
        predictions_manifest["external_labels_read"]
        or len(predictions_manifest["runs"]) != contract["expected_candidate_runs"]
    ):
        raise ValueError("The full label-blind prediction gate has not passed")
    for run in predictions_manifest["runs"]:
        completion = load_hashed(
            args.prediction_root / run["run_id"] / "PREDICTION_COMPLETION.json",
            "prediction_completion_sha256",
        )
        if completion["prediction_completion_sha256"] != run["prediction_completion_sha256"]:
            raise ValueError(f"Prediction completion changed: {run['run_id']}")
        for output in completion["panel_outputs"]:
            path = args.prediction_root / run["run_id"] / f"{output['panel']}_predictions.csv"
            if sha256(path) != output["sha256"]:
                raise ValueError(f"Prediction output changed: {run['run_id']} {output['panel']}")
    if {row["reference"] for row in predictions_manifest.get("references", [])} != {
        "starting_pretrained",
        "full_dft_posttrained",
    }:
        raise ValueError("Both scientific reference predictions must complete before labels open")
    for reference in predictions_manifest["references"]:
        completion = load_hashed(
            args.prediction_root
            / "_references"
            / reference["reference"]
            / "REFERENCE_COMPLETION.json",
            "reference_completion_sha256",
        )
        if completion["reference_completion_sha256"] != reference["reference_completion_sha256"]:
            raise ValueError(f"Reference completion changed: {reference['reference']}")
        for output in completion["panel_outputs"]:
            path = (
                args.prediction_root
                / "_references"
                / reference["reference"]
                / f"{output['panel']}_predictions.csv"
            )
            if sha256(path) != output["sha256"]:
                raise ValueError(
                    f"Reference prediction changed: {reference['reference']} {output['panel']}"
                )

    labels = {}
    with ZipFile(args.archive) as archive:
        for panel, spec in contract["panels"].items():
            member = spec["archive_prefix"] + "/manifest.json"
            labels[panel] = json.loads(archive.read(member))
            if len(labels[panel]) != spec["records"]:
                raise ValueError(f"External label count differs for {panel}")

    run_metadata = {}
    launch = load_hashed(args.launch_manifest, "launch_sha256")
    if launch["launch_sha256"] != contract["launch_sha256"]:
        raise ValueError("Launch manifest differs from the frozen evaluation contract")
    for row in launch["runs"]:
        run_metadata[row["run_id"]] = row
    results = []
    reference_results = []
    for reference in predictions_manifest["references"]:
        for panel in sorted(contract["panels"]):
            predictions = read_predictions(
                args.prediction_root
                / "_references"
                / reference["reference"]
                / f"{panel}_predictions.csv"
            )
            joined = join(labels[panel], predictions)
            if panel == "dft_pbe":
                reference_results.append(
                    {
                        "reference": reference["reference"],
                        "panel": panel,
                        "source": "all",
                        **evaluate(joined, 100),
                    }
                )
            else:
                groups = defaultdict(list)
                for row in joined:
                    groups[row["model_key"]].append(row)
                for source, source_rows in sorted(groups.items()):
                    reference_results.append(
                        {
                            "reference": reference["reference"],
                            "panel": panel,
                            "source": source,
                            **evaluate(source_rows, 100),
                        }
                    )
    for run in predictions_manifest["runs"]:
        metadata = run_metadata[run["run_id"]]
        for panel in sorted(contract["panels"]):
            predictions = read_predictions(
                args.prediction_root / run["run_id"] / f"{panel}_predictions.csv"
            )
            joined = join(labels[panel], predictions)
            if panel == "dft_pbe":
                metrics = evaluate(joined, 100)
                results.append(
                    {
                        "run_id": run["run_id"],
                        **metadata,
                        "panel": panel,
                        "source": "all",
                        **metrics,
                    }
                )
            else:
                groups = defaultdict(list)
                for row in joined:
                    groups[row["model_key"]].append(row)
                for source, source_rows in sorted(groups.items()):
                    metrics = evaluate(source_rows, 100)
                    results.append(
                        {
                            "run_id": run["run_id"],
                            **metadata,
                            "panel": panel,
                            "source": source,
                            **metrics,
                        }
                    )

    dft = [row for row in results if row["panel"] == "dft_pbe"]
    starting_top100 = next(
        row["top_k_stable_rate"]
        for row in reference_results
        if row["reference"] == "starting_pretrained" and row["panel"] == "dft_pbe"
    )
    for row in dft:
        row["top100_utility_vs_starting_checkpoint"] = row["top_k_stable_rate"] - starting_top100
    grouped: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in dft:
        grouped[int(row["budget_structures"])][row["candidate"]].append(row["top_k_stable_rate"])
    decisions = []
    predicted_order = contract["frozen_candidate_prediction"]["complete_order"]
    for budget, candidates in sorted(grouped.items()):
        if set(candidates) != set(predicted_order) or any(
            len(values) != 2 for values in candidates.values()
        ):
            raise ValueError(f"Incomplete candidate-by-seed matrix at budget {budget}")
        utilities = {
            candidate: math.fsum(values) / len(values) for candidate, values in candidates.items()
        }
        best_value = max(utilities.values())
        best = sorted(candidate for candidate, value in utilities.items() if value == best_value)
        selected = predicted_order[0]
        seed_winners = []
        for seed_index in range(2):
            seed_values = {
                candidate: candidates[candidate][seed_index] for candidate in predicted_order
            }
            seed_best = max(seed_values.values())
            seed_winners.append(
                sorted(candidate for candidate, value in seed_values.items() if value == seed_best)
            )
        decisions.append(
            {
                "budget_structures": budget,
                "predicted_best": selected,
                "observed_best": best,
                "predicted_best_correct": selected in best,
                "allocation_regret": best_value - utilities[selected],
                "pairwise_order_accuracy": pairwise_order_accuracy(predicted_order, utilities),
                "seed_winners": seed_winners,
                "seed_winner_agreement": seed_winners[0] == seed_winners[1],
                "two_seed_mean_top100_stable_rate": utilities,
            }
        )
    summary = {
        "schema_version": "1.0",
        "status": "external_outcomes_scored_after_complete_prediction_gate",
        "prediction_manifest_sha256": predictions_manifest["prediction_manifest_sha256"],
        "external_labels_opened": True,
        "run_metrics": results,
        "reference_metrics": reference_results,
        "candidate_decisions": decisions,
        "decision_summary": {
            "best_candidate_accuracy": sum(row["predicted_best_correct"] for row in decisions)
            / len(decisions),
            "mean_allocation_regret": math.fsum(row["allocation_regret"] for row in decisions)
            / len(decisions),
            "mean_pairwise_order_accuracy": math.fsum(
                row["pairwise_order_accuracy"] for row in decisions
            )
            / len(decisions),
            "seed_winner_agreement_rate": sum(row["seed_winner_agreement"] for row in decisions)
            / len(decisions),
        },
    }
    summary["score_sha256"] = canonical_digest(summary)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary["decision_summary"], indent=2, sort_keys=True))
    print(f"score_sha256={summary['score_sha256']}")


if __name__ == "__main__":
    main()
