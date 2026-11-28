#!/usr/bin/env python3
"""Fit and score frozen pairwise rankers on domain-aware utility panels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass, replace
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MaxAbsScaler

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "DOMAIN_AWARE_UTILITY_INPUTS.jsonl"
LABELS = HERE / "DOMAIN_AWARE_UTILITY_LABELS.jsonl"
SPLITS = HERE / "DOMAIN_AWARE_NESTED_SPLITS.json"
MANIFEST = HERE / "DOMAIN_AWARE_TRAINING_VIEW.json"
CONTRACT = HERE / "DOMAIN_PAIRWISE_RANKER_CONTRACT.json"
BASELINE_RESULTS = HERE / "DOMAIN_STRUCTURED_RESULTS.json"
PREDICTIONS = HERE / "DOMAIN_PAIRWISE_RANKER_PREDICTIONS.jsonl"
FITS = HERE / "DOMAIN_PAIRWISE_RANKER_FITS.json"
RESULTS = HERE / "DOMAIN_PAIRWISE_RANKER_RESULTS.json"

METHODS = ("structured_pairwise_ranker", "structured_text_pairwise_ranker")
MINIMUM_REGRET_IMPROVEMENT = 1e-6
PRIMARY_SUITES = {
    "controlled_leave_one_study_out",
    "coding_leave_one_decision_out",
    "materials_leave_one_study_out",
    "finance_leave_one_study_out",
}
CS = (0.01, 0.1, 1.0, 10.0)
RANDOM_STATE = 1729


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key_digest(keys: list[str]) -> str:
    payload = "".join(f"{key}\n" for key in sorted(keys))
    return hashlib.sha256(payload.encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


@dataclass(frozen=True)
class Candidate:
    candidate_key: str
    panel_key: str
    study_key: str
    structured: dict[str, Any]
    text: dict[str, str]
    scoring: dict[str, Any]
    utility: float | None


def load_candidates(include_outcomes: bool) -> list[Candidate]:
    manifest = json.loads(MANIFEST.read_text())
    if manifest["artifacts"]["inputs"]["sha256"] != sha256(INPUTS):
        raise ValueError("domain-aware input digest mismatch")
    if manifest["artifacts"]["protected_labels"]["sha256"] != sha256(LABELS):
        raise ValueError("domain-aware protected-label digest mismatch")
    if manifest["artifacts"]["nested_splits"]["sha256"] != sha256(SPLITS):
        raise ValueError("domain-aware nested-split digest mismatch")
    inputs = {row["candidate_key"]: row for row in read_jsonl(INPUTS)}
    labels = {row["candidate_key"]: row for row in read_jsonl(LABELS)}
    if inputs.keys() != labels.keys():
        raise ValueError("input and protected-label candidate keys differ")
    rows = []
    for key in sorted(inputs):
        source = inputs[key]
        label = labels[key]
        rows.append(
            Candidate(
                candidate_key=key,
                panel_key=source["partition"]["panel_key"],
                study_key=source["partition"]["study_key"],
                structured=source["feature_views"]["structured"],
                text=source["feature_views"]["text"],
                scoring=label["scoring"],
                utility=(
                    float(label["outcome"]["within_panel_normalized_utility"])
                    if include_outcomes
                    else None
                ),
            )
        )
    return rows


def open_training_outcomes(candidates: list[Candidate]) -> list[Candidate]:
    """Attach outcomes only to candidates inside the active fitting partition."""
    allowed = {candidate.candidate_key for candidate in candidates}
    outcomes = {
        row["candidate_key"]: float(row["outcome"]["within_panel_normalized_utility"])
        for row in read_jsonl(LABELS)
        if row["candidate_key"] in allowed
    }
    if outcomes.keys() != allowed:
        raise ValueError("active fitting outcomes do not match requested candidate keys")
    return [
        replace(candidate, utility=outcomes[candidate.candidate_key]) for candidate in candidates
    ]


def flatten(value: Any, prefix: str = "") -> dict[str, float | str]:
    result: dict[str, float | str] = {}
    if isinstance(value, dict):
        for key, child in sorted(value.items()):
            path = f"{prefix}.{key}" if prefix else key
            result.update(flatten(child, path))
    elif isinstance(value, bool):
        result[prefix] = float(value)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            result[prefix] = number
    elif isinstance(value, str):
        result[prefix] = value
    elif (
        isinstance(value, list)
        and value
        and all(isinstance(item, (int, float, bool)) for item in value)
    ):
        numbers = np.asarray(value, dtype=float)
        if np.isfinite(numbers).all():
            result[f"{prefix}.length"] = float(len(numbers))
            result[f"{prefix}.mean"] = float(numbers.mean())
            result[f"{prefix}.sd"] = float(numbers.std())
    return result


def structured_features(candidate: Candidate) -> dict[str, float | str]:
    features = flatten(candidate.structured)
    domain = str(candidate.structured["domain"])
    measurements = candidate.structured.get("prediction_time_measurements", {})
    for key, value in flatten(measurements).items():
        features[f"domain_measurement.{domain}.{key}"] = value
    return features


def text_features(candidate: Candidate) -> str:
    return (
        f"intervention {candidate.text['candidate_intervention']} "
        f"context {candidate.text['decision_context']}"
    )


class FeatureEncoder:
    def __init__(self, candidates: list[Candidate], include_text: bool):
        self.structured = DictVectorizer(sparse=True, sort=True)
        matrix = self.structured.fit_transform([structured_features(row) for row in candidates])
        self.scaler = MaxAbsScaler().fit(matrix)
        self.text: TfidfVectorizer | None = None
        if include_text:
            self.text = TfidfVectorizer(
                lowercase=True,
                max_features=4096,
                ngram_range=(1, 2),
                sublinear_tf=True,
            )
            self.text.fit([text_features(row) for row in candidates])

    def transform(self, candidates: list[Candidate]) -> sparse.csr_matrix:
        structured = self.scaler.transform(
            self.structured.transform([structured_features(row) for row in candidates])
        )
        if self.text is None:
            return sparse.csr_matrix(structured)
        text = self.text.transform([text_features(row) for row in candidates])
        return sparse.hstack((structured, text), format="csr")

    @property
    def columns(self) -> int:
        text_columns = 0 if self.text is None else len(self.text.get_feature_names_out())
        return len(self.structured.get_feature_names_out()) + text_columns


def groups_by_panel(candidates: list[Candidate]) -> list[list[int]]:
    panels: dict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        panels[candidate.panel_key].append(index)
    return [panels[key] for key in sorted(panels)]


def pairwise_training_data(
    candidates: list[Candidate], matrix: sparse.csr_matrix
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray]:
    difference_blocks = []
    label_blocks = []
    weight_blocks = []
    for indices in groups_by_panel(candidates):
        pairs = [
            (left, right)
            for left, right in combinations(indices, 2)
            if not math.isclose(
                float(candidates[left].utility),
                float(candidates[right].utility),
                rel_tol=0,
                abs_tol=1e-12,
            )
        ]
        if not pairs:
            continue
        weight = 1.0 / (2.0 * len(pairs))
        left = np.asarray([pair[0] for pair in pairs], dtype=int)
        right = np.asarray([pair[1] for pair in pairs], dtype=int)
        delta = matrix[left] - matrix[right]
        positive = np.asarray(
            [
                float(candidates[left_index].utility) > float(candidates[right_index].utility)
                for left_index, right_index in pairs
            ],
            dtype=int,
        )
        difference_blocks.extend((delta, -delta))
        label_blocks.extend((positive, 1 - positive))
        weight_blocks.extend((np.full(len(pairs), weight), np.full(len(pairs), weight)))
    if not difference_blocks:
        raise ValueError("pairwise ranker requires at least one non-tied training pair")
    return (
        sparse.vstack(difference_blocks, format="csr"),
        np.concatenate(label_blocks),
        np.concatenate(weight_blocks),
    )


def prepare_fit(
    train: list[Candidate], test: list[Candidate], method: str
) -> tuple[sparse.csr_matrix, np.ndarray, np.ndarray, sparse.csr_matrix, int]:
    encoder = FeatureEncoder(train, include_text=method == "structured_text_pairwise_ranker")
    train_matrix = encoder.transform(train)
    pair_x, pair_y, pair_weight = pairwise_training_data(train, train_matrix)
    return pair_x, pair_y, pair_weight, encoder.transform(test), encoder.columns


def fit_prepared(
    pair_x: sparse.csr_matrix,
    pair_y: np.ndarray,
    pair_weight: np.ndarray,
    test_matrix: sparse.csr_matrix,
    c_value: float,
) -> np.ndarray:
    model = LogisticRegression(
        C=c_value,
        fit_intercept=False,
        max_iter=2000,
        random_state=RANDOM_STATE,
        solver="liblinear",
    )
    model.fit(pair_x, pair_y, sample_weight=pair_weight)
    return model.decision_function(test_matrix)


def fit_predict(
    train: list[Candidate],
    test: list[Candidate],
    method: str,
    c_value: float,
) -> tuple[np.ndarray, int, int]:
    pair_x, pair_y, pair_weight, test_matrix, columns = prepare_fit(train, test, method)
    return (
        fit_prepared(pair_x, pair_y, pair_weight, test_matrix, c_value),
        columns,
        len(pair_y),
    )


def panel_rows(candidates: list[Candidate], predictions: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for indices in groups_by_panel(candidates):
        actual = np.asarray([float(candidates[index].utility) for index in indices])
        predicted = np.asarray([predictions[index] for index in indices])
        chosen = np.flatnonzero(np.isclose(predicted, predicted.max(), rtol=0, atol=1e-12))
        observed_best = np.flatnonzero(np.isclose(actual, actual.max(), rtol=0, atol=1e-12))
        ordering = []
        for left, right in combinations(range(len(indices)), 2):
            observed_sign = np.sign(actual[left] - actual[right])
            predicted_sign = np.sign(predicted[left] - predicted[right])
            ordering.append(
                0.5
                if observed_sign == 0 or predicted_sign == 0
                else float(observed_sign == predicted_sign)
            )
        rows.append(
            {
                "domain": candidates[indices[0]].scoring["domain"],
                "study_id": candidates[indices[0]].scoring["study_id"],
                "panel_id": candidates[indices[0]].scoring["panel_id"],
                "normalized_regret": float(actual.max() - actual[chosen].mean()),
                "pairwise_ordering": float(np.mean(ordering)) if ordering else 0.5,
                "top_choice_credit": float(np.mean(np.isin(chosen, observed_best))),
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_study: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_study[row["study_id"]].append(row)
    fields = ("normalized_regret", "pairwise_ordering", "top_choice_credit")
    return {
        "studies": len(by_study),
        "panels": len(rows),
        **{
            f"study_macro_{field}": float(
                np.mean([np.mean([row[field] for row in group]) for group in by_study.values()])
            )
            for field in fields
        },
    }


def split_candidates(
    candidates: list[Candidate], selector: dict[str, str]
) -> tuple[list[Candidate], list[Candidate]]:
    field = selector["field"]
    if field not in {"study_id", "domain"}:
        raise ValueError(f"unsupported frozen split field: {field}")
    test = [candidate for candidate in candidates if candidate.scoring[field] == selector["value"]]
    test_keys = {candidate.candidate_key for candidate in test}
    train = [candidate for candidate in candidates if candidate.candidate_key not in test_keys]
    return train, test


def validate_split(
    train: list[Candidate], test: list[Candidate], fold: dict[str, Any], test_name: str
) -> None:
    expected_test_name = "validation" if test_name == "validation" else "test"
    for name, rows in (("train", train), (expected_test_name, test)):
        if len(rows) != fold[f"{name}_candidates"]:
            raise ValueError(f"{fold['fold_id']} {name} count mismatch")
        if key_digest([row.candidate_key for row in rows]) != fold[f"{name}_candidate_keys_sha256"]:
            raise ValueError(f"{fold['fold_id']} {name} digest mismatch")
    if fold["retrieval_history_candidate_keys_sha256"] != fold["train_candidate_keys_sha256"]:
        raise ValueError(f"{fold['fold_id']} retrieval history differs from fitting partition")


def select_c(
    train: list[Candidate], inner_folds: list[dict[str, Any]], method: str
) -> tuple[float, dict[str, float]]:
    losses = {value: [] for value in CS}
    for fold in inner_folds:
        inner_train, validation = split_candidates(train, fold["validation_selector"])
        validate_split(inner_train, validation, fold, "validation")
        pair_x, pair_y, pair_weight, validation_matrix, _ = prepare_fit(
            inner_train, validation, method
        )
        for value in CS:
            predictions = fit_prepared(pair_x, pair_y, pair_weight, validation_matrix, value)
            summary = summarize(panel_rows(validation, predictions))
            losses[value].append(summary["study_macro_normalized_regret"])
    means = {str(value): float(np.mean(losses[value])) for value in CS}
    selected = min(CS, key=lambda value: (means[str(value)], value))
    return selected, means


def predict() -> dict[str, Any]:
    candidates = load_candidates(include_outcomes=False)
    split_artifact = json.loads(SPLITS.read_text())
    prediction_rows = []
    fit_receipts = []
    for suite in split_artifact["suites"]:
        if suite["suite_id"] not in PRIMARY_SUITES:
            continue
        selected = [
            candidate
            for candidate in candidates
            if all(candidate.scoring[field] == value for field, value in suite["filters"].items())
        ]
        if (
            len(selected) != suite["candidates"]
            or key_digest([row.candidate_key for row in selected]) != suite["candidate_keys_sha256"]
        ):
            raise ValueError(f"frozen suite mismatch: {suite['suite_id']}")
        for fold in suite["folds"]:
            train, test = split_candidates(selected, fold["test_selector"])
            validate_split(train, test, fold, "test")
            train = open_training_outcomes(train)
            for method in METHODS:
                selected_c, inner_losses = select_c(train, fold["inner_folds"], method)
                values, columns, pair_rows = fit_predict(train, test, method, selected_c)
                fit_receipts.append(
                    {
                        "suite_id": suite["suite_id"],
                        "fold_id": fold["fold_id"],
                        "method": method,
                        "selected_C": selected_c,
                        "inner_study_macro_regret": inner_losses,
                        "feature_columns": columns,
                        "pairwise_training_rows": pair_rows,
                        "train_candidates": len(train),
                        "test_candidates": len(test),
                    }
                )
                for candidate, value in zip(test, values, strict=True):
                    prediction_rows.append(
                        {
                            "suite_id": suite["suite_id"],
                            "fold_id": fold["fold_id"],
                            "method": method,
                            "candidate_key": candidate.candidate_key,
                            "predicted_panel_utility": float(value),
                        }
                    )
    PREDICTIONS.write_text("".join(canonical(row) + "\n" for row in prediction_rows))
    receipt = {
        "artifact": "anarres_domain_pairwise_ranker_fit_receipt_v1",
        "status": "predictions written and hashed before outer-fold scoring",
        "contract_sha256": sha256(CONTRACT),
        "predictions": {"rows": len(prediction_rows), "sha256": sha256(PREDICTIONS)},
        "fits": fit_receipts,
    }
    FITS.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def score(receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    if receipt is None:
        receipt = json.loads(FITS.read_text())
    if receipt["contract_sha256"] != sha256(CONTRACT):
        raise ValueError("pairwise-ranker contract changed after fitting")
    if receipt["predictions"]["sha256"] != sha256(PREDICTIONS):
        raise ValueError("prediction digest differs from the fit receipt")
    candidates = {row.candidate_key: row for row in load_candidates(include_outcomes=True)}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(PREDICTIONS):
        grouped[(row["suite_id"], row["method"])].append(row)
    suites: dict[str, dict[str, Any]] = {}
    for (suite_id, method), rows in sorted(grouped.items()):
        test = [candidates[row["candidate_key"]] for row in rows]
        predictions = np.asarray([float(row["predicted_panel_utility"]) for row in rows])
        metrics = panel_rows(test, predictions)
        summary = summarize(metrics)
        summary["domains"] = {
            domain: summarize([row for row in metrics if row["domain"] == domain])
            for domain in sorted({row["domain"] for row in metrics})
        }
        suites.setdefault(suite_id, {})[method] = summary

    baseline = json.loads(BASELINE_RESULTS.read_text())["suites"]
    comparisons = {}
    for suite_id in sorted(suites):
        ridge = baseline[suite_id]["measurement_ridge"]
        comparisons[suite_id] = {}
        for method, metrics in suites[suite_id].items():
            comparisons[suite_id][method] = {
                "regret_change_vs_measurement_ridge": (
                    metrics["study_macro_normalized_regret"]
                    - ridge["study_macro_normalized_regret"]
                ),
                "ordering_change_vs_measurement_ridge": (
                    metrics["study_macro_pairwise_ordering"]
                    - ridge["study_macro_pairwise_ordering"]
                ),
                "improves_regret": (
                    ridge["study_macro_normalized_regret"]
                    - metrics["study_macro_normalized_regret"]
                    > MINIMUM_REGRET_IMPROVEMENT
                ),
            }
    eligible = []
    for method in METHODS:
        improves_all = all(comparisons[suite_id][method]["improves_regret"] for suite_id in suites)
        ordering_changes = [
            comparisons[suite_id][method]["ordering_change_vs_measurement_ridge"]
            for suite_id in suites
        ]
        eligible.append(
            {
                "method": method,
                "improves_regret_on_every_primary_suite": improves_all,
                "mean_ordering_change_vs_measurement_ridge": float(np.mean(ordering_changes)),
                "passes": improves_all and float(np.mean(ordering_changes)) >= 0,
            }
        )
    model_performance_passed = any(row["passes"] for row in eligible)
    cost_criterion_scored = False
    abstention_criterion_scored = False
    passed = model_performance_passed and cost_criterion_scored and abstention_criterion_scored
    result = {
        "artifact": "anarres_domain_pairwise_ranker_results_v1",
        "evidence_tier": "retrospective nested development replay",
        "inputs": {
            "training_view_sha256": sha256(MANIFEST),
            "nested_splits_sha256": sha256(SPLITS),
            "contract_sha256": sha256(CONTRACT),
            "predictions_sha256": sha256(PREDICTIONS),
            "fit_receipt_sha256": sha256(FITS),
            "structured_baseline_results_sha256": sha256(BASELINE_RESULTS),
        },
        "methods": list(METHODS),
        "suites": suites,
        "comparisons": comparisons,
        "advancement_gate": {
            "methods": eligible,
            "model_performance_passed": model_performance_passed,
            "cost_criterion_scored": cost_criterion_scored,
            "abstention_criterion_scored": abstention_criterion_scored,
            "passed": passed,
            "prospective_freeze_permitted": passed,
            "decision": (
                "freeze the passing ranker for a new prospective study"
                if passed
                else "do not advance either learned ranker to a prospective claim"
            ),
        },
        "cost_boundary": (
            "The fit receipt records feature and pairwise-training sizes, but portable elapsed "
            "runtime and complete measurement, training, failure, and evaluation costs are not "
            "yet comparable across the native studies. The cost criterion remains unscored."
        ),
        "claim_boundary": (
            "Retrospective development replay only. The same studies informed the archive "
            "and this model comparison; real training and protected evaluation remain the verifier."
        ),
    }
    RESULTS.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--predict", action="store_true")
    actions.add_argument("--score", action="store_true")
    actions.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.predict:
        print(json.dumps(predict(), indent=2, sort_keys=True))
    elif args.score:
        print(json.dumps(score(), indent=2, sort_keys=True))
    else:
        receipt = predict()
        print(json.dumps(score(receipt), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
