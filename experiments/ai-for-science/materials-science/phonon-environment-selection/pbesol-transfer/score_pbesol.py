#!/usr/bin/env python3
"""Verify the sealed prediction gate, open frozen PBEsol labels, and score."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import tarfile
from collections import defaultdict
from pathlib import Path


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


def auc(labels: list[bool], scores: list[float]) -> float:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("AUC requires both stable and unstable structures")
    ordered = sorted(range(len(scores)), key=lambda index: (scores[index], index))
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
    credit = total = 0.0
    for left in range(len(scores)):
        for right in range(left + 1, len(scores)):
            target_sign = (targets[left] > targets[right]) - (targets[left] < targets[right])
            if target_sign == 0:
                continue
            score_sign = (scores[left] > scores[right]) - (scores[left] < scores[right])
            total += 1
            credit += 0.5 if score_sign == 0 else float(score_sign == target_sign)
    if total == 0:
        raise ValueError("Continuous concordance has no comparable pairs")
    return credit / total


def evaluate(rows: list[dict], threshold: float, top_k: int) -> dict:
    labels = [float(row["min_frequency"]) > threshold for row in rows]
    targets = [float(row["min_frequency"]) for row in rows]
    composite = [float(row["composite_score"]) for row in rows]
    probabilities = [float(row["threshold_probability_minus_0p1"]) for row in rows]
    predictions = [float(row["prediction"]) for row in rows]
    if not all(math.isfinite(value) for value in targets + composite + predictions):
        raise ValueError("A scored value is not finite")
    if not all(math.isfinite(value) and 0 <= value <= 1 for value in probabilities):
        raise ValueError("Threshold probabilities must be finite and lie in [0, 1]")
    if top_k > len(rows):
        raise ValueError("Top-k exceeds the panel size")
    order = sorted(range(len(rows)), key=lambda index: (-composite[index], rows[index]["local_id"]))
    return {
        "records": len(rows),
        "stable_records": sum(labels),
        "stable_fraction": sum(labels) / len(labels),
        "top_k": top_k,
        "top_k_stable_rate": sum(labels[index] for index in order[:top_k]) / top_k,
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


def join(labels: dict[str, dict], predictions: list[dict]) -> list[dict]:
    by_id = {row["local_id"]: row for row in predictions}
    if len(by_id) != len(predictions) or set(by_id) != set(labels):
        raise ValueError("Predictions and frozen PBEsol labels do not match one-to-one")
    return [{**labels[material_id], **by_id[material_id]} for material_id in labels]


def pairwise_order_accuracy(order: list[str], values: dict[str, float]) -> float:
    credit = total = 0.0
    for left in range(len(order)):
        for right in range(left + 1, len(order)):
            total += 1
            difference = values[order[left]] - values[order[right]]
            credit += 1.0 if difference > 0 else (0.5 if difference == 0 else 0.0)
    return credit / total


def validate_prediction_gate(
    contract: dict,
    sealed_manifest_path: Path,
    prediction_root: Path,
) -> dict:
    sealed = load_hashed(sealed_manifest_path, "prediction_manifest_sha256")
    live_path = prediction_root / "PREDICTION_MANIFEST.json"
    if sha256(live_path) != sha256(sealed_manifest_path):
        raise ValueError("Live prediction manifest differs from the committed sealed manifest")
    live = load_hashed(live_path, "prediction_manifest_sha256")
    if live != sealed:
        raise ValueError("Live and sealed prediction manifests differ")
    if live["evaluation_contract_sha256"] != contract["evaluation_contract_file_sha256"]:
        raise ValueError("Prediction manifest is bound to a different evaluation contract")
    if live["external_labels_read"]:
        raise ValueError("Prediction manifest claims that external labels were already read")
    if len(live["runs"]) != contract["expected_candidate_runs"]:
        raise ValueError("Candidate prediction matrix is incomplete")

    for run in live["runs"]:
        run_id = run["run_id"]
        completion = load_hashed(
            prediction_root / run_id / "PREDICTION_COMPLETION.json",
            "prediction_completion_sha256",
        )
        if completion["prediction_completion_sha256"] != run["prediction_completion_sha256"]:
            raise ValueError(f"Prediction completion changed: {run_id}")
        outputs = {row["panel"]: row for row in completion["panel_outputs"]}
        if set(outputs) != {"pbesol"} or outputs["pbesol"]["records"] != 1000:
            raise ValueError(f"Unexpected panel output for {run_id}")
        output = prediction_root / run_id / "pbesol_predictions.csv"
        if sha256(output) != outputs["pbesol"]["sha256"]:
            raise ValueError(f"Prediction output changed: {run_id}")

    expected_references = set(contract["expected_reference_checkpoints"])
    references = {row["reference"]: row for row in live["references"]}
    if set(references) != expected_references:
        raise ValueError("Reference prediction matrix is incomplete")
    for name, record in references.items():
        completion = load_hashed(
            prediction_root / "_references" / name / "REFERENCE_COMPLETION.json",
            "reference_completion_sha256",
        )
        if completion["reference_completion_sha256"] != record["reference_completion_sha256"]:
            raise ValueError(f"Reference completion changed: {name}")
        outputs = {row["panel"]: row for row in completion["panel_outputs"]}
        if set(outputs) != {"pbesol"} or outputs["pbesol"]["records"] != 1000:
            raise ValueError(f"Unexpected reference panel output: {name}")
        output = prediction_root / "_references" / name / "pbesol_predictions.csv"
        if sha256(output) != outputs["pbesol"]["sha256"]:
            raise ValueError(f"Reference output changed: {name}")
    return live


def open_frozen_labels(
    source_shard: Path,
    freeze: dict,
    expected_threshold: float,
) -> dict[str, dict]:
    labels = {}
    with tarfile.open(source_shard, "r") as archive:
        for record in freeze["records"]:
            material_id = record["material_id"]
            member = record["poscar_member"].removesuffix("POSCAR.gz") + "summary.json.gz"
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"Missing frozen summary: {material_id}")
            summary = json.loads(gzip.decompress(extracted.read()))
            if summary["mp_id"] != material_id:
                raise ValueError(f"Summary identity mismatch: {material_id}")
            threshold = float(summary["positivity_threshold_thz"])
            minimum = float(summary["min_frequency"])
            if threshold != expected_threshold or not math.isfinite(minimum):
                raise ValueError(f"Invalid frozen outcome: {material_id}")
            labels[material_id] = {
                "local_id": material_id,
                "min_frequency": minimum,
                "stable": minimum > expected_threshold,
            }
    if len(labels) != len(freeze["records"]):
        raise ValueError("Frozen labels are not one-to-one")
    return labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-shard", type=Path, required=True)
    parser.add_argument("--panel-freeze", type=Path, required=True)
    parser.add_argument("--evaluation-contract", type=Path, required=True)
    parser.add_argument("--launch-manifest", type=Path, required=True)
    parser.add_argument("--sealed-prediction-manifest", type=Path, required=True)
    parser.add_argument("--prediction-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    contract = load_hashed(args.evaluation_contract, "evaluation_contract_sha256")
    contract["evaluation_contract_file_sha256"] = sha256(args.evaluation_contract)
    if sha256(args.source_shard) != contract["source_shard_sha256"]:
        raise ValueError("PBEsol source shard differs from the frozen contract")
    freeze = load_hashed(args.panel_freeze, "panel_freeze_sha256")
    if sha256(args.panel_freeze) != contract["panel_freeze_file_sha256"]:
        raise ValueError("Panel freeze file differs from the frozen contract")
    if freeze["panel_freeze_sha256"] != contract["panel_freeze_sha256"]:
        raise ValueError("Panel freeze digest differs from the frozen contract")
    if freeze["external_labels_read"]:
        raise ValueError("Panel freeze claims that external labels were read")
    launch = load_hashed(args.launch_manifest, "launch_sha256")
    if launch["launch_sha256"] != contract["launch_sha256"]:
        raise ValueError("Launch manifest differs from the frozen contract")
    run_metadata = {row["run_id"]: row for row in launch["runs"]}
    if len(run_metadata) != contract["expected_candidate_runs"]:
        raise ValueError("Launch matrix is incomplete")

    predictions = validate_prediction_gate(
        contract, args.sealed_prediction_manifest, args.prediction_root
    )
    if args.verify_only:
        print("Prediction gate verified; PBEsol outcomes remain unopened.")
        return
    threshold = float(contract["outcome_source"]["expected_positivity_threshold_thz"])
    labels = open_frozen_labels(args.source_shard, freeze, threshold)

    top_k = 100
    run_metrics = []
    for run in predictions["runs"]:
        metadata = run_metadata[run["run_id"]]
        rows = join(
            labels,
            read_predictions(args.prediction_root / run["run_id"] / "pbesol_predictions.csv"),
        )
        run_metrics.append({**metadata, **evaluate(rows, threshold, top_k)})

    reference_metrics = []
    for reference in predictions["references"]:
        name = reference["reference"]
        rows = join(
            labels,
            read_predictions(
                args.prediction_root / "_references" / name / "pbesol_predictions.csv"
            ),
        )
        reference_metrics.append({"reference": name, **evaluate(rows, threshold, top_k)})
    starting = next(
        row["top_k_stable_rate"]
        for row in reference_metrics
        if row["reference"] == "starting_pretrained"
    )
    for row in run_metrics:
        row["top100_utility_vs_starting_checkpoint"] = row["top_k_stable_rate"] - starting

    grouped: dict[int, dict[str, list[tuple[int, float]]]] = defaultdict(lambda: defaultdict(list))
    for row in run_metrics:
        grouped[int(row["budget_structures"])][row["candidate"]].append(
            (int(row["seed"]), row["top_k_stable_rate"])
        )

    decisions = []
    expected_candidates = set(contract["expected_candidates"])
    expected_seeds = set(contract["expected_seeds"])
    for budget, candidate_rows in sorted(grouped.items()):
        order = contract["frozen_candidate_prediction"]["complete_order_by_budget"][str(budget)]
        predicted_best = contract["frozen_candidate_prediction"]["best_by_budget"][str(budget)]
        if set(candidate_rows) != expected_candidates or set(order) != expected_candidates:
            raise ValueError(f"Candidate set is incomplete at budget {budget}")
        by_candidate = {candidate: dict(sorted(rows)) for candidate, rows in candidate_rows.items()}
        if any(set(rows) != expected_seeds for rows in by_candidate.values()):
            raise ValueError(f"Seed matrix is incomplete at budget {budget}")
        means = {
            candidate: math.fsum(rows.values()) / len(rows)
            for candidate, rows in by_candidate.items()
        }
        best_value = max(means.values())
        observed_best = sorted(
            candidate for candidate, value in means.items() if value == best_value
        )
        seed_winners = {}
        for seed in sorted(expected_seeds):
            seed_values = {candidate: rows[seed] for candidate, rows in by_candidate.items()}
            seed_best = max(seed_values.values())
            seed_winners[str(seed)] = sorted(
                candidate for candidate, value in seed_values.items() if value == seed_best
            )
        decisions.append(
            {
                "budget_structures": budget,
                "frozen_complete_order": order,
                "predicted_best": predicted_best,
                "observed_best": observed_best,
                "predicted_best_correct": predicted_best in observed_best,
                "allocation_regret": best_value - means[predicted_best],
                "pairwise_order_accuracy": pairwise_order_accuracy(order, means),
                "seed_winners": seed_winners,
                "seed_winner_agreement": len({tuple(v) for v in seed_winners.values()}) == 1,
                "two_seed_mean_top100_stable_rate": means,
            }
        )

    result = {
        "schema_version": "1.0",
        "study": contract["study"],
        "status": "pbesol_outcomes_scored_after_complete_prediction_gate",
        "prediction_manifest_sha256": predictions["prediction_manifest_sha256"],
        "source_shard_sha256": contract["source_shard_sha256"],
        "panel_freeze_sha256": freeze["panel_freeze_sha256"],
        "external_labels_opened": True,
        "panel": {
            "records": len(labels),
            "stable_records": sum(row["stable"] for row in labels.values()),
            "stable_fraction": sum(row["stable"] for row in labels.values()) / len(labels),
            "threshold_thz": threshold,
        },
        "run_metrics": run_metrics,
        "reference_metrics": reference_metrics,
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
    result["score_sha256"] = canonical_digest(result)
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["decision_summary"], indent=2, sort_keys=True))
    print(f"score_sha256={result['score_sha256']}")


if __name__ == "__main__":
    main()
