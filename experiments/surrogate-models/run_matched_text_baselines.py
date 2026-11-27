#!/usr/bin/env python3
"""Fit matched text baselines on the record-conditioned replay."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import build_record_conditioned_replay as replay
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "RECORD_CONDITIONED_CONTRACT.json"
OUTPUT = HERE / "MATCHED_TEXT_BASELINE_RESULTS.json"

METHODS = {
    "tfidf_ridge": ("ridge", (0.01, 0.1, 1.0, 10.0, 100.0)),
    "tfidf_knn": ("knn", (1, 2, 3, 5, 8)),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_text(row: dict[str, Any], measurements: bool) -> str:
    record = {
        "environment": replay.environment(row),
        "intervention": replay.intervention(row, measurements),
    }
    return json.dumps(record, sort_keys=True, ensure_ascii=False)


def fit_predict(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    measurements: bool,
    family: str,
    parameter: float,
) -> np.ndarray:
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        lowercase=True,
        ngram_range=(3, 5),
        min_df=1,
        sublinear_tf=True,
    )
    train_matrix = vectorizer.fit_transform([record_text(row, measurements) for row in train])
    test_matrix = vectorizer.transform([record_text(row, measurements) for row in test])
    targets = np.asarray([row["normalized_utility"] for row in train], dtype=float)
    if family == "ridge":
        model = Ridge(alpha=float(parameter), solver="lsqr")
    else:
        model = KNeighborsRegressor(
            n_neighbors=min(int(parameter), len(train)),
            weights="distance",
            metric="cosine",
            algorithm="brute",
        )
    model.fit(train_matrix, targets)
    return np.clip(np.asarray(model.predict(test_matrix), dtype=float), 0.0, 1.0)


def panel_score(rows: list[dict[str, Any]], predictions: np.ndarray) -> dict[str, float]:
    actual = np.asarray([row["normalized_utility"] for row in rows], dtype=float)
    maximum = float(np.max(predictions))
    chosen = np.flatnonzero(np.isclose(predictions, maximum, rtol=0, atol=1e-12))
    pairwise = []
    for left, right in combinations(range(len(rows)), 2):
        observed_sign = np.sign(actual[left] - actual[right])
        predicted_sign = np.sign(predictions[left] - predictions[right])
        pairwise.append(
            0.5
            if observed_sign == 0 or predicted_sign == 0
            else float(observed_sign == predicted_sign)
        )
    best = float(np.max(actual))
    return {
        "normalized_regret": best - float(np.mean(actual[chosen])),
        "pairwise_ordering": float(np.mean(pairwise)) if pairwise else 0.5,
        "top_choice_credit": float(np.mean(np.isclose(actual[chosen], best))),
    }


def evaluate(
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    measurements: bool,
    family: str,
    parameter: float,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    predicted = fit_predict(train, test, measurements, family, parameter)
    panels: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(test):
        panels[(row["study_id"], row["panel_id"])].append(index)
    scores = []
    for (study, panel), indices in sorted(panels.items()):
        metrics = panel_score([test[index] for index in indices], predicted[indices])
        scores.append({"study_id": study, "panel_id": panel, **metrics})
    summary = {
        metric: float(np.mean([row[metric] for row in scores]))
        for metric in ("normalized_regret", "pairwise_ordering", "top_choice_credit")
    }
    return scores, summary


def select_parameter(
    rows: list[dict[str, Any]], measurements: bool, family: str, parameters: tuple[float, ...]
) -> float:
    studies = sorted({row["study_id"] for row in rows})
    eligible = [value for value in parameters if family != "knn" or value <= len(rows)]
    scored = []
    for parameter in eligible:
        fold_regrets = []
        for study in studies:
            train = [row for row in rows if row["study_id"] != study]
            test = [row for row in rows if row["study_id"] == study]
            if not train or not test:
                continue
            _, summary = evaluate(train, test, measurements, family, parameter)
            fold_regrets.append(summary["normalized_regret"])
        scored.append((float(np.mean(fold_regrets)), float(parameter)))
    return min(scored)[1]


def run() -> dict[str, Any]:
    rows = replay.aggregate()
    studies = sorted({row["study_id"] for row in rows})
    all_results: dict[str, Any] = {}
    for measurements in (False, True):
        condition = "with_measurements" if measurements else "without_measurements"
        for method, (family, parameters) in METHODS.items():
            folds = []
            for study in studies:
                train = [row for row in rows if row["study_id"] != study]
                test = [row for row in rows if row["study_id"] == study]
                parameter = select_parameter(train, measurements, family, parameters)
                panels, summary = evaluate(train, test, measurements, family, parameter)
                folds.append(
                    {
                        "heldout_study": study,
                        "selected_parameter": parameter,
                        "panels": panels,
                        **summary,
                    }
                )
            all_results[f"{method}_{condition}"] = {
                "folds": folds,
                **{
                    f"study_macro_{metric}": float(np.mean([fold[metric] for fold in folds]))
                    for metric in (
                        "normalized_regret",
                        "pairwise_ordering",
                        "top_choice_credit",
                    )
                },
            }
    return {
        "artifact": "anarres_matched_text_baselines_v1",
        "evidence_tier": "retrospective complete-study replay",
        "contract_sha256": sha256(CONTRACT),
        "methods": all_results,
        "claim_boundary": (
            "Text baselines use the same held-out studies and prediction-time fields as the "
            "record-conditioned comparison. They are not prospective evidence."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        raise SystemExit("Pass --run to fit and score the frozen text baselines.")
    result = run()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
