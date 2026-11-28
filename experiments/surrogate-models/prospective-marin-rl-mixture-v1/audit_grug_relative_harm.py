#!/usr/bin/env python3
"""Audit target-level relative harm against the released Harrier mixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import run_grug_swarm_baselines as baselines

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "GRUG_SWARM_RELATIVE_HARM_RESULTS.json"
REFERENCE_LINEAGE = "mixture-b5f5f18766de58f382ac9774"


def average_precision(observed: np.ndarray, score: np.ndarray) -> float:
    order = np.argsort(-score, kind="stable")
    observed = observed[order]
    score = score[order]
    true_positives = np.cumsum(observed)
    false_positives = np.cumsum(~observed)
    thresholds = np.r_[np.where(np.diff(score))[0], len(score) - 1]
    recall = true_positives[thresholds] / true_positives[-1]
    precision = true_positives[thresholds] / (
        true_positives[thresholds] + false_positives[thresholds]
    )
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def roc_auc(observed: np.ndarray, score: np.ndarray) -> float:
    positive = score[observed]
    negative = score[~observed]
    comparison = positive[:, None] - negative[None, :]
    return float((np.sum(comparison > 0) + 0.5 * np.sum(comparison == 0)) / comparison.size)


def target_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
    reference: np.ndarray,
    target_indices: np.ndarray,
) -> dict:
    rows = []
    for target in target_indices:
        regressed = observed[:, target] > reference[target]
        risk = predicted[:, target] - reference[target]
        top_count = max(1, int(np.ceil(0.2 * len(risk))))
        top_risk = np.argsort(-risk, kind="stable")[:top_count]
        prevalence = float(np.mean(regressed))
        recall = float(np.sum(regressed[top_risk]) / np.sum(regressed))
        rows.append(
            {
                "prevalence": prevalence,
                "roc_auc": roc_auc(regressed, risk),
                "average_precision": average_precision(regressed, risk),
                "recall_in_top_risk_20pct": recall,
                "top_risk_recall_lift": recall / 0.2,
                "direction_accuracy": float(np.mean((risk > 0) == regressed)),
            }
        )
    return {
        "targets": len(rows),
        **{key: float(np.mean([row[key] for row in rows])) for key in rows[0]},
    }


def cross_fitted_predictions(
    features: np.ndarray,
    outcomes: np.ndarray,
    folds: np.ndarray,
    lineages: np.ndarray,
    predictor,
) -> np.ndarray:
    predictions = np.zeros_like(outcomes)
    for fold in sorted(set(folds)):
        test = (folds == fold) & (lineages != REFERENCE_LINEAGE)
        train = (folds != fold) & (lineages != REFERENCE_LINEAGE)
        predictions[test] = predictor(features[train], outcomes[train], features[test])
    return predictions


def build() -> dict:
    inputs = baselines.read_rows(baselines.INPUTS)
    labels = {row["record_key"]: row for row in baselines.read_rows(baselines.LABELS)}
    outcome_rows = labels[inputs[0]["record_key"]]["outcomes"]
    target_families = np.asarray([row["family"] for row in outcome_rows])
    raw = np.asarray(
        [
            row["prediction_time"]["phase0_cell_weights"]
            + row["prediction_time"]["phase1_cell_weights"]
            for row in inputs
        ],
        dtype=float,
    )
    content_basis = np.asarray(baselines.read_gzip_json(baselines.CONTENT)["matrix"], dtype=float)
    content = np.concatenate([raw[:, :200] @ content_basis, raw[:, 200:] @ content_basis], axis=1)
    outcomes = np.asarray(
        [[outcome["value"] for outcome in labels[row["record_key"]]["outcomes"]] for row in inputs],
        dtype=float,
    )
    lineages = np.asarray([row["lineage_key"] for row in inputs])
    design_families = np.asarray([row["design_family"] for row in inputs])
    reference = outcomes[lineages == REFERENCE_LINEAGE].mean(axis=0)
    candidate_lineages = sorted(set(lineages) - {REFERENCE_LINEAGE})
    lineage_outcomes = np.asarray(
        [outcomes[lineages == lineage].mean(axis=0) for lineage in candidate_lineages]
    )
    splits = {
        "lineage_five_fold": np.asarray([baselines.lineage_fold(lineage) for lineage in lineages]),
        "leave_one_design_family_out": design_families,
    }
    models = {
        "training_mean": (raw, baselines.mean_predictor),
        "hellinger_rbf_kernel": (raw, baselines.kernel_predictor),
        "content_hellinger_rbf_kernel": (content, baselines.kernel_predictor),
    }
    results = {}
    for split_name, folds in splits.items():
        results[split_name] = {}
        for model_name, (features, predictor) in models.items():
            predictions = cross_fitted_predictions(features, outcomes, folds, lineages, predictor)
            lineage_predictions = np.asarray(
                [predictions[lineages == lineage].mean(axis=0) for lineage in candidate_lineages]
            )
            by_family = {}
            for family in sorted(set(target_families)):
                indices = np.where(target_families == family)[0]
                by_family[family] = target_metrics(
                    lineage_outcomes, lineage_predictions, reference, indices
                )
            results[split_name][model_name] = {
                "all_targets": target_metrics(
                    lineage_outcomes,
                    lineage_predictions,
                    reference,
                    np.arange(outcomes.shape[1]),
                ),
                "by_target_family": by_family,
            }
    return baselines.rounded(
        {
            "artifact": "anarres_grug_swarm_relative_harm_audit_v1",
            "status": "retrospective development result; not calibrated prospective risk",
            "inputs": {
                "corpus_manifest_sha256": baselines.digest(baselines.CORPUS),
                "inputs_sha256": baselines.digest(baselines.INPUTS),
                "protected_labels_sha256": baselines.digest(baselines.LABELS),
                "content_basis_sha256": baselines.digest(baselines.CONTENT),
            },
            "contract": {
                "reference_lineage": REFERENCE_LINEAGE,
                "reference_runs": int(np.sum(lineages == REFERENCE_LINEAGE)),
                "candidate_lineages": len(candidate_lineages),
                "targets": outcomes.shape[1],
                "label": (
                    "a candidate's lineage-mean native metric is greater than the released "
                    "Harrier reference mean; every native metric is lower-is-better"
                ),
                "fit_exclusion": (
                    "the reference and each candidate's complete held-out lineage or design "
                    "family are excluded from model fitting"
                ),
            },
            "results": results,
            "interpretation_boundary": (
                "The zero-margin label provides target-level relative-harm triage against an "
                "already-run reference. Only three reference runs are available, targets are "
                "correlated, and no probability calibration is claimed. A prospective panel "
                "must freeze a material regression margin before candidate outcomes open."
            ),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        if json.loads(RESULTS.read_text()) != expected:
            raise SystemExit("stale Grug relative-harm result")
        return
    RESULTS.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
