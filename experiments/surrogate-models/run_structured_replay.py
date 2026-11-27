#!/usr/bin/env python3
"""Fit and score the frozen structured surrogate replay without row leakage."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "MODEL_INPUTS.jsonl"
LABELS = HERE / "MODEL_LABELS.jsonl"
VIEWS = HERE / "MODEL_VIEWS.json"
SPLITS = HERE / "REPLAY_SPLITS.json"
CONTRACT = HERE / "BASELINE_CONTRACT.json"
BASELINE_AUDIT = HERE / "BASELINE_AUDIT.json"
PREDICTIONS = HERE / "STRUCTURED_REPLAY_PREDICTIONS.jsonl"
FITS = HERE / "STRUCTURED_REPLAY_FITS.json"
RESULTS = HERE / "STRUCTURED_REPLAY_RESULTS.json"

PRIMARY_SUITES = {
    "seed_level_leave_one_study_out",
    "materials_leave_one_publication_out",
    "finance_leave_one_study_out",
}
METHODS = (
    "uninformed_tie",
    "metadata_ridge",
    "measurement_ridge",
    "small_tree_ensemble",
)
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
TREE_GRID = (
    {"max_depth": 4, "min_samples_leaf": 5},
    {"max_depth": 8, "min_samples_leaf": 5},
    {"max_depth": None, "min_samples_leaf": 10},
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def nested(value: dict[str, Any], field: str) -> Any:
    current: Any = value
    for part in field.split("."):
        current = current[part]
    return current


def record_digest(rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(f"{row['record_id']}\n" for row in sorted(rows, key=lambda x: x["record_id"]))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Record:
    join_key: str
    features: dict[str, Any]
    record_id: str
    scoring: dict[str, Any]


def load_records() -> list[Record]:
    views = json.loads(VIEWS.read_text())
    if sha256(INPUTS) != views["inputs"]["sha256"]:
        raise ValueError("model-input digest mismatch")
    if sha256(LABELS) != views["labels"]["sha256"]:
        raise ValueError("protected-label digest mismatch")
    input_rows = {row["join_key"]: row for row in read_jsonl(INPUTS)}
    label_rows = {row["join_key"]: row for row in read_jsonl(LABELS)}
    if input_rows.keys() != label_rows.keys():
        raise ValueError("input and protected-label joins differ")
    return [
        Record(
            join_key=key,
            features=input_rows[key]["features"],
            record_id=label_rows[key]["record_id"],
            scoring=label_rows[key]["scoring"],
        )
        for key in sorted(input_rows)
    ]


def load_outcomes(allowed: set[str] | None = None) -> dict[str, dict[str, Any]]:
    outcomes = {}
    for row in read_jsonl(LABELS):
        if allowed is None or row["join_key"] in allowed:
            outcomes[row["join_key"]] = row["outcome"]
    if allowed is not None and outcomes.keys() != allowed:
        raise ValueError("requested training outcomes do not match protected labels")
    return outcomes


def matches(record: Record, filters: dict[str, Any]) -> bool:
    view = {**record.scoring, "grouping": record.scoring["grouping"]}
    return all(nested(view, field) == expected for field, expected in filters.items())


def feature_leaves(value: Any, prefix: str = "") -> Iterable[tuple[str, float]]:
    if isinstance(value, dict):
        for key, child in sorted(value.items()):
            path = f"{prefix}.{key}" if prefix else key
            yield from feature_leaves(child, path)
    elif isinstance(value, bool):
        yield prefix, float(value)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            yield prefix, number
    elif (
        isinstance(value, list)
        and value
        and all(isinstance(item, (int, float, bool)) for item in value)
    ):
        numbers = np.asarray(value, dtype=float)
        if np.isfinite(numbers).all():
            yield f"{prefix}.length", float(len(numbers))
            yield f"{prefix}.mean", float(numbers.mean())
            yield f"{prefix}.sd", float(numbers.std())


def raw_features(record: Record, method: str) -> tuple[dict[str, float], set[str]]:
    values: dict[str, float] = {}
    categories = {
        f"domain={record.features['domain']}",
        f"evidence_level={record.features['evidence_level']}",
    }
    for path, value in feature_leaves(record.features.get("cost", {}), "cost"):
        values[path] = value
    if method == "measurement_ridge":
        domain = record.features["domain"]
        for path, value in feature_leaves(record.features.get("prediction_time", {})):
            values[f"native.{domain}.{path}"] = value
    return values, categories


class Vectorizer:
    def __init__(self, records: list[Record], method: str):
        observed = [raw_features(record, method) for record in records]
        self.numeric = sorted({key for values, _ in observed for key in values})
        self.categories = sorted({key for _, categories in observed for key in categories})
        matrix = np.asarray(
            [[values.get(key, np.nan) for key in self.numeric] for values, _ in observed],
            dtype=float,
        )
        if self.numeric:
            with np.errstate(invalid="ignore"):
                means = np.nanmean(matrix, axis=0)
                scales = np.nanstd(matrix, axis=0)
            self.means = np.where(np.isfinite(means), means, 0.0)
            self.scales = np.where(np.isfinite(scales) & (scales > 0), scales, 1.0)
        else:
            self.means = np.zeros(0)
            self.scales = np.ones(0)
        self.method = method

    def transform(self, records: list[Record]) -> np.ndarray:
        rows = []
        for record in records:
            values, categories = raw_features(record, self.method)
            raw = np.asarray([values.get(key, np.nan) for key in self.numeric], dtype=float)
            missing = np.isnan(raw).astype(float)
            numeric = np.where(np.isnan(raw), self.means, raw)
            numeric = (numeric - self.means) / self.scales
            categorical = np.asarray([float(key in categories) for key in self.categories])
            rows.append(np.concatenate([numeric, missing, categorical]))
        return np.asarray(rows, dtype=float)

    @property
    def columns(self) -> int:
        return 2 * len(self.numeric) + len(self.categories)


def panel_key(record: Record) -> tuple[str, str, str]:
    return record.scoring["study_id"], record.scoring["source_id"], record.scoring["panel_id"]


def candidate_key(record: Record) -> tuple[str, str, str, str]:
    return (*panel_key(record), record.scoring["candidate_id"])


def aggregate_candidates(
    records: list[Record], outcomes: dict[str, dict[str, Any]] | None
) -> list[tuple[Record, float, int, tuple[str, ...]]]:
    grouped: dict[tuple[str, str, str, str], list[Record]] = defaultdict(list)
    for record in records:
        grouped[candidate_key(record)].append(record)
    result = []
    for key in sorted(grouped):
        rows = grouped[key]
        feature_encodings = {canonical(row.features) for row in rows}
        if len(feature_encodings) != 1:
            raise ValueError(f"prediction-time features vary inside candidate lineage: {key}")
        join_keys = tuple(sorted(row.join_key for row in rows))
        outcome = math.nan
        if outcomes is not None:
            directions = {outcomes[row.join_key]["higher_is_better"] for row in rows}
            if len(directions) != 1:
                raise ValueError(f"outcome direction varies inside candidate lineage: {key}")
            values = [float(outcomes[row.join_key]["value"]) for row in rows]
            oriented = values if directions.pop() else [-value for value in values]
            outcome = float(np.mean(oriented))
        result.append((rows[0], outcome, len(rows), join_keys))
    return result


def normalized_targets(candidates: list[tuple[Record, float, int, tuple[str, ...]]]) -> np.ndarray:
    by_panel: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, (record, _, _, _) in enumerate(candidates):
        by_panel[panel_key(record)].append(index)
    targets = np.zeros(len(candidates), dtype=float)
    for indices in by_panel.values():
        values = np.asarray([candidates[index][1] for index in indices])
        spread = float(values.max() - values.min())
        normalized = np.full(len(indices), 0.5) if spread == 0 else (values - values.min()) / spread
        for index, value in zip(indices, normalized, strict=True):
            targets[index] = value
    return targets


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    x_mean = x.mean(axis=0)
    y_mean = float(y.mean())
    centered = x - x_mean
    u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    weights = vt.T @ ((singular / (singular**2 + alpha)) * (u.T @ (y - y_mean)))
    intercept = y_mean - float(x_mean @ weights)
    return weights, intercept


def predict_ridge(
    train: list[tuple[Record, float, int, tuple[str, ...]]],
    test: list[tuple[Record, float, int, tuple[str, ...]]],
    method: str,
    alpha: float,
) -> tuple[np.ndarray, int]:
    train_records = [row[0] for row in train]
    test_records = [row[0] for row in test]
    vectorizer = Vectorizer(train_records, method)
    x_train = vectorizer.transform(train_records)
    x_test = vectorizer.transform(test_records)
    weights, intercept = fit_ridge(x_train, normalized_targets(train), alpha)
    return x_test @ weights + intercept, vectorizer.columns


def predict_ridge_grid(
    train: list[tuple[Record, float, int, tuple[str, ...]]],
    test: list[tuple[Record, float, int, tuple[str, ...]]],
    method: str,
) -> dict[float, np.ndarray]:
    train_records = [row[0] for row in train]
    test_records = [row[0] for row in test]
    vectorizer = Vectorizer(train_records, method)
    x_train = vectorizer.transform(train_records)
    x_test = vectorizer.transform(test_records)
    y = normalized_targets(train)
    x_mean = x_train.mean(axis=0)
    y_mean = float(y.mean())
    centered = x_train - x_mean
    u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    projected_y = u.T @ (y - y_mean)
    result = {}
    for alpha in ALPHAS:
        weights = vt.T @ ((singular / (singular**2 + alpha)) * projected_y)
        intercept = y_mean - float(x_mean @ weights)
        result[alpha] = x_test @ weights + intercept
    return result


def panel_regret(
    candidates: list[tuple[Record, float, int, tuple[str, ...]]], predictions: np.ndarray
) -> float:
    metrics = score_panels(candidates, predictions)
    studies: dict[str, list[float]] = defaultdict(list)
    for row in metrics:
        studies[row["study_id"]].append(row["normalized_regret"])
    return float(np.mean([np.mean(values) for values in studies.values()]))


def choose_alpha(train: list[tuple[Record, float, int, tuple[str, ...]]], method: str) -> float:
    studies = sorted({row[0].scoring["study_id"] for row in train})
    if len(studies) < 3:
        return 10.0
    losses: dict[float, list[float]] = {alpha: [] for alpha in ALPHAS}
    for study in studies:
        inner_train = [row for row in train if row[0].scoring["study_id"] != study]
        validation = [row for row in train if row[0].scoring["study_id"] == study]
        prediction_grid = predict_ridge_grid(inner_train, validation, method)
        for alpha, predictions in prediction_grid.items():
            losses[alpha].append(panel_regret(validation, predictions))
    return min(ALPHAS, key=lambda alpha: (float(np.mean(losses[alpha])), -alpha))


def predict_tree(
    train: list[tuple[Record, float, int, tuple[str, ...]]],
    test: list[tuple[Record, float, int, tuple[str, ...]]],
    parameters: dict[str, int | None],
) -> tuple[np.ndarray, int]:
    from sklearn.ensemble import ExtraTreesRegressor

    train_records = [row[0] for row in train]
    test_records = [row[0] for row in test]
    vectorizer = Vectorizer(train_records, "measurement_ridge")
    model = ExtraTreesRegressor(
        n_estimators=64,
        max_depth=parameters["max_depth"],
        min_samples_leaf=int(parameters["min_samples_leaf"]),
        max_features=0.5,
        bootstrap=False,
        random_state=1729,
        n_jobs=1,
    )
    model.fit(vectorizer.transform(train_records), normalized_targets(train))
    return model.predict(vectorizer.transform(test_records)), vectorizer.columns


def choose_tree_parameters(
    train: list[tuple[Record, float, int, tuple[str, ...]]],
) -> dict[str, int | None]:
    studies = sorted({row[0].scoring["study_id"] for row in train})
    if len(studies) < 8:
        raise ValueError("small tree ensemble requires at least eight independent groups")
    losses: list[tuple[float, int, dict[str, int | None]]] = []
    for order, parameters in enumerate(TREE_GRID):
        fold_losses = []
        for study in studies:
            inner_train = [row for row in train if row[0].scoring["study_id"] != study]
            validation = [row for row in train if row[0].scoring["study_id"] == study]
            predictions, _ = predict_tree(inner_train, validation, parameters)
            fold_losses.append(panel_regret(validation, predictions))
        losses.append((float(np.mean(fold_losses)), order, parameters))
    return min(losses, key=lambda row: (row[0], row[1]))[2]


def score_panels(
    candidates: list[tuple[Record, float, int, tuple[str, ...]]], predictions: np.ndarray
) -> list[dict[str, Any]]:
    by_panel: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, (record, _, _, _) in enumerate(candidates):
        by_panel[panel_key(record)].append(index)
    rows = []
    for key, indices in sorted(by_panel.items()):
        actual = np.asarray([candidates[index][1] for index in indices])
        predicted = np.asarray([predictions[index] for index in indices])
        spread = float(actual.max() - actual.min())
        normalized = np.full(len(indices), 0.5) if spread == 0 else (actual - actual.min()) / spread
        chosen = np.flatnonzero(np.isclose(predicted, predicted.max(), rtol=0, atol=1e-12))
        observed_best = np.flatnonzero(np.isclose(actual, actual.max(), rtol=0, atol=1e-12))
        pair_scores = []
        for left, right in combinations(range(len(indices)), 2):
            observed_sign = np.sign(actual[left] - actual[right])
            predicted_sign = np.sign(predicted[left] - predicted[right])
            pair_scores.append(
                0.5
                if observed_sign == 0 or predicted_sign == 0
                else float(observed_sign == predicted_sign)
            )
        control = [
            local
            for local, index in enumerate(indices)
            if candidates[index][0].scoring["grouping"].get("role") == "control"
        ]
        regression = None
        if len(control) == 1:
            regression = float(np.mean(actual[chosen] < actual[control[0]]))
        rows.append(
            {
                "study_id": key[0],
                "source_id": key[1],
                "panel_id": key[2],
                "candidates": len(indices),
                "normalized_regret": float(normalized.max() - normalized[chosen].mean()),
                "pairwise_ordering": float(np.mean(pair_scores)) if pair_scores else 0.5,
                "top_choice_credit": float(np.mean(np.isin(chosen, observed_best))),
                "regression_selection": regression,
            }
        )
    return rows


def summarize(panel_rows: list[dict[str, Any]]) -> dict[str, Any]:
    study_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in panel_rows:
        study_rows[row["study_id"]].append(row)
    fields = ("normalized_regret", "pairwise_ordering", "top_choice_credit")
    result = {
        "studies": len(study_rows),
        "panels": len(panel_rows),
        **{
            f"study_macro_{field}": float(
                np.mean([np.mean([row[field] for row in rows]) for rows in study_rows.values()])
            )
            for field in fields
        },
    }
    regression_by_study = [
        np.mean(
            [row["regression_selection"] for row in rows if row["regression_selection"] is not None]
        )
        for rows in study_rows.values()
        if any(row["regression_selection"] is not None for row in rows)
    ]
    result["study_macro_regression_selection"] = (
        float(np.mean(regression_by_study)) if regression_by_study else None
    )
    return result


def suite_records(records: list[Record], suite: dict[str, Any]) -> list[Record]:
    selected = [record for record in records if matches(record, suite["filters"])]
    digest_rows = [{"record_id": record.record_id} for record in selected]
    if (
        len(selected) != suite["records"]
        or record_digest(digest_rows) != suite["record_ids_sha256"]
    ):
        raise ValueError(f"frozen suite mismatch: {suite['suite_id']}")
    return selected


def split_fold(selected: list[Record], fold: dict[str, Any]) -> tuple[list[Record], list[Record]]:
    field = fold["test_selector"]["field"]
    value = fold["test_selector"]["value"]
    test = [record for record in selected if nested({**record.scoring}, field) == value]
    test_keys = {record.join_key for record in test}
    train = [record for record in selected if record.join_key not in test_keys]
    for name, rows in (("train", train), ("test", test)):
        digest_rows = [{"record_id": record.record_id} for record in rows]
        if len(rows) != fold[f"{name}_records"]:
            raise ValueError(f"{fold['fold_id']} {name} count mismatch")
        if record_digest(digest_rows) != fold[f"{name}_record_ids_sha256"]:
            raise ValueError(f"{fold['fold_id']} {name} digest mismatch")
    return train, test


def predict() -> dict[str, Any]:
    records = load_records()
    split_artifact = json.loads(SPLITS.read_text())
    prediction_rows = []
    fit_receipts = []
    for suite in split_artifact["suites"]:
        if suite["suite_id"] not in PRIMARY_SUITES:
            continue
        selected = suite_records(records, suite)
        for fold in suite["folds"]:
            train_records, test_records = split_fold(selected, fold)
            train_outcomes = load_outcomes({record.join_key for record in train_records})
            train = aggregate_candidates(train_records, train_outcomes)
            test = aggregate_candidates(test_records, None)
            for method in METHODS:
                groups = {row[0].scoring["study_id"] for row in train}
                if method == "small_tree_ensemble" and len(groups) < 8:
                    continue
                if method == "uninformed_tie":
                    values = np.zeros(len(test))
                    alpha = None
                    parameters = None
                    columns = 0
                elif method == "small_tree_ensemble":
                    parameters = choose_tree_parameters(train)
                    values, columns = predict_tree(train, test, parameters)
                    alpha = None
                else:
                    alpha = choose_alpha(train, method)
                    values, columns = predict_ridge(train, test, method, alpha)
                    parameters = None
                fit_receipts.append(
                    {
                        "suite_id": suite["suite_id"],
                        "fold_id": fold["fold_id"],
                        "method": method,
                        "alpha": alpha,
                        "parameters": parameters,
                        "feature_columns": columns,
                        "train_candidates": len(train),
                        "test_candidates": len(test),
                    }
                )
                for (_record, _, seeds, join_keys), value in zip(test, values, strict=True):
                    prediction_rows.append(
                        {
                            "suite_id": suite["suite_id"],
                            "fold_id": fold["fold_id"],
                            "method": method,
                            "join_keys": list(join_keys),
                            "candidate_seed_records": seeds,
                            "predicted_panel_utility": float(value),
                        }
                    )
    content = "".join(canonical(row) + "\n" for row in prediction_rows)
    PREDICTIONS.write_text(content)
    receipt = {
        "status": "predictions_written_before_heldout_scoring",
        "rows": len(prediction_rows),
        "sha256": sha256(PREDICTIONS),
        "fit_receipts": fit_receipts,
    }
    FITS.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def score(prediction_receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    if not PREDICTIONS.exists():
        raise ValueError("predictions must be written before held-out scoring")
    if prediction_receipt is None:
        if not FITS.exists():
            raise ValueError("fit receipt is missing")
        prediction_receipt = json.loads(FITS.read_text())
    if prediction_receipt["sha256"] != sha256(PREDICTIONS):
        raise ValueError("prediction digest does not match fit receipt")
    records = load_records()
    by_join = {record.join_key: record for record in records}
    outcomes = load_outcomes()
    predictions = read_jsonl(PREDICTIONS)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in predictions:
        grouped[(row["suite_id"], row["method"])].append(row)
    summaries = {}
    for (suite_id, method), rows in sorted(grouped.items()):
        candidates = []
        values = []
        for row in rows:
            join_keys = tuple(row["join_keys"])
            record = by_join[join_keys[0]]
            directions = {outcomes[key]["higher_is_better"] for key in join_keys}
            if len(directions) != 1:
                raise ValueError("outcome direction varies inside scored candidate")
            observed = [float(outcomes[key]["value"]) for key in join_keys]
            if not directions.pop():
                observed = [-value for value in observed]
            candidates.append(
                (record, float(np.mean(observed)), row["candidate_seed_records"], join_keys)
            )
            values.append(float(row["predicted_panel_utility"]))
        summaries.setdefault(suite_id, {})[method] = summarize(
            score_panels(candidates, np.asarray(values))
        )
    comparisons = {}
    for suite_id, eligible in summaries.items():
        measurement = eligible["measurement_ridge"]
        simple_method = min(
            ("uninformed_tie", "metadata_ridge"),
            key=lambda method: eligible[method]["study_macro_normalized_regret"],
        )
        simple = eligible[simple_method]
        measurement_regression = measurement["study_macro_regression_selection"]
        simple_regression = simple["study_macro_regression_selection"]
        regression_pass = (
            True
            if measurement_regression is None or simple_regression is None
            else measurement_regression <= simple_regression
        )
        comparisons[suite_id] = {
            "measurement_ridge_regret": measurement["study_macro_normalized_regret"],
            "strongest_simple_method": simple_method,
            "strongest_simple_regret": simple["study_macro_normalized_regret"],
            "regret_improvement": (
                simple["study_macro_normalized_regret"]
                - measurement["study_macro_normalized_regret"]
            ),
            "measurement_regression_selection": measurement_regression,
            "strongest_simple_regression_selection": simple_regression,
            "passes_regret": (
                measurement["study_macro_normalized_regret"]
                < simple["study_macro_normalized_regret"]
            ),
            "passes_regression": regression_pass,
        }
    regret_and_regression_pass = all(
        row["passes_regret"] and row["passes_regression"] for row in comparisons.values()
    )
    cost_criterion_scored = False
    abstention_criterion_scored = False
    gate_passed = (
        regret_and_regression_pass and cost_criterion_scored and abstention_criterion_scored
    )
    result = {
        "artifact": "anarres_structured_surrogate_replay_v1",
        "evidence_tier": "retrospective grouped replay",
        "inputs": {
            "model_inputs_sha256": sha256(INPUTS),
            "protected_labels_sha256": sha256(LABELS),
            "replay_splits_sha256": sha256(SPLITS),
            "baseline_contract_sha256": sha256(CONTRACT),
            "baseline_audit_sha256": sha256(BASELINE_AUDIT),
            "predictions_sha256": sha256(PREDICTIONS),
            "fit_receipt_sha256": sha256(FITS),
        },
        "methods": list(METHODS),
        "suites": summaries,
        "advancement_gate": {
            "criterion": (
                "Measurement ridge must improve study-macro normalized regret over the "
                "strongest simple baseline on every complete-study suite, retain the gain "
                "after costs, avoid increased regression selection, and declare abstention."
            ),
            "comparisons": comparisons,
            "regret_and_regression_pass": regret_and_regression_pass,
            "cost_criterion_scored": cost_criterion_scored,
            "abstention_criterion_scored": abstention_criterion_scored,
            "passed": gate_passed,
            "prospective_followup_authorized": gate_passed,
            "decision": (
                "advance to a prospectively frozen follow-up"
                if gate_passed
                else "do not advance this structured predictor to a prospective test"
            ),
        },
        "prediction_receipt": prediction_receipt,
        "claim_boundary": (
            "Retrospective replay only. Results do not establish prospective validity or "
            "replace candidate training and held-out evaluation."
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
