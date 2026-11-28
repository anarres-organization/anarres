#!/usr/bin/env python3
"""Fit and score a gate for using retrieved experimental history."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MaxAbsScaler

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "DOMAIN_RECORD_CONDITIONED_INPUTS.jsonl"
BASE_PREDICTIONS = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTIONS.jsonl"
BASE_RECEIPT = HERE / "DOMAIN_RECORD_CONDITIONED_PREDICTION_RECEIPT.json"
LABELS = HERE / "DOMAIN_RECORD_CONDITIONED_LABELS.jsonl"
CONTRACT = HERE / "HISTORY_SUPPORT_GATE_CONTRACT.json"
PREDICTIONS = HERE / "HISTORY_SUPPORT_GATE_PREDICTIONS.jsonl"
FITS = HERE / "HISTORY_SUPPORT_GATE_FITS.json"
RESULTS = HERE / "HISTORY_SUPPORT_GATE_RESULTS.json"

SPEC = importlib.util.spec_from_file_location(
    "record_conditioned_scorer", HERE / "score_record_conditioned_model.py"
)
assert SPEC and SPEC.loader
SCORER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCORER
SPEC.loader.exec_module(SCORER)

ZERO = "zero_history_with_measurements"
HISTORY = "retrieved_history_with_measurements"
CS = (0.01, 0.1, 1.0, 10.0)
RANDOM_STATE = 1729
ABSTENTION_MARGIN = 0.10


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


@dataclass(frozen=True)
class Panel:
    study: str
    panel: str
    domain: str
    zero_input: dict[str, Any]
    history_input: dict[str, Any]
    zero_prediction: dict[str, Any]
    history_prediction: dict[str, Any]
    label: dict[str, Any] | None = None


def load_panels() -> list[Panel]:
    receipt = json.loads(BASE_RECEIPT.read_text())
    if receipt["predictions_sha256"] != sha256(BASE_PREDICTIONS):
        raise ValueError("base prediction receipt mismatch")
    inputs = {row["prompt_id"]: row for row in read_jsonl(INPUTS)}
    predictions = {row["prompt_id"]: row for row in read_jsonl(BASE_PREDICTIONS)}
    if inputs.keys() != predictions.keys():
        raise ValueError("base inputs and predictions differ")
    grouped: dict[tuple[str, str], dict[str, tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(
        dict
    )
    for prompt_id, source in inputs.items():
        if source["condition"] in {ZERO, HISTORY}:
            grouped[(source["heldout_study"], source["target_panel"])][source["condition"]] = (
                source,
                predictions[prompt_id],
            )
    panels = []
    for (study, panel), conditions in sorted(grouped.items()):
        if set(conditions) != {ZERO, HISTORY}:
            raise ValueError(f"missing measured condition for {study}/{panel}")
        zero_input, zero_prediction = conditions[ZERO]
        history_input, history_prediction = conditions[HISTORY]
        target = json.loads(zero_input["user"])["target_environment"]
        panels.append(
            Panel(
                study=study,
                panel=panel,
                domain=target["domain"].replace(" ", "_"),
                zero_input=zero_input,
                history_input=history_input,
                zero_prediction=zero_prediction,
                history_prediction=history_prediction,
            )
        )
    return panels


def open_training_labels(panels: list[Panel]) -> list[Panel]:
    label_by_prompt = {row["prompt_id"]: row for row in read_jsonl(LABELS)}
    result = []
    for panel in panels:
        prompt_id = panel.zero_input["prompt_id"]
        if prompt_id not in label_by_prompt:
            raise ValueError("active fitting panel lacks a protected label")
        result.append(replace(panel, label=label_by_prompt[prompt_id]))
    return result


def support_features(panel: Panel) -> dict[str, float | str]:
    zero_user = json.loads(panel.zero_input["user"])
    history_user = json.loads(panel.history_input["user"])
    target = zero_user["target_environment"]
    target_tokens = tokens(target["decision_context"] + " " + target["evaluation_metric"])
    similarities = []
    same_domain = 0
    same_metric = 0
    for source in history_user["retrieved_experimental_panels"]:
        environment = source["environment"]
        source_tokens = tokens(
            environment["decision_context"] + " " + environment["evaluation_metric"]
        )
        similarities.append(
            len(target_tokens & source_tokens) / max(1, len(target_tokens | source_tokens))
        )
        same_domain += int(environment["domain"] == target["domain"])
        same_metric += int(environment["evaluation_metric"] == target["evaluation_metric"])
    numeric_measurements = [
        float(value)
        for candidate in zero_user["target_candidates"]
        for value in candidate.get("prediction_time_measurements", {}).values()
        if isinstance(value, (int, float, bool)) and math.isfinite(float(value))
    ]
    zero_forecast = panel.zero_prediction["prediction"]
    return {
        "domain": panel.domain,
        "target_candidates": float(len(zero_user["target_candidates"])),
        "retrieved_same_domain": float(same_domain),
        "retrieved_same_metric": float(same_metric),
        "retrieval_similarity_max": float(max(similarities, default=0.0)),
        "retrieval_similarity_mean": float(np.mean(similarities)) if similarities else 0.0,
        "measurement_values": float(len(numeric_measurements)),
        "measurement_dispersion": (
            float(np.std(numeric_measurements)) if numeric_measurements else 0.0
        ),
        "zero_forecast_confidence": float(zero_forecast["confidence"]),
        "zero_forecast_abstained": float(zero_forecast["abstain"]),
    }


def condition_metrics(panel: Panel, condition: str) -> dict[str, float | bool]:
    if panel.label is None:
        raise ValueError("protected label is unavailable")
    row = panel.zero_prediction if condition == ZERO else panel.history_prediction
    return SCORER.panel_metrics(row["prediction"], panel.label)


def history_helped(panel: Panel) -> int:
    zero = float(condition_metrics(panel, ZERO)["normalized_regret"])
    history = float(condition_metrics(panel, HISTORY)["normalized_regret"])
    return int(history < zero - 1e-12)


class Gate:
    def __init__(self, candidates: list[Panel], c_value: float):
        self.vectorizer = DictVectorizer(sparse=True, sort=True)
        matrix = self.vectorizer.fit_transform([support_features(row) for row in candidates])
        self.scaler = MaxAbsScaler().fit(matrix)
        labels = np.asarray([history_helped(row) for row in candidates])
        self.constant = float(labels.mean()) if len(set(labels)) < 2 else None
        self.model: LogisticRegression | None = None
        if self.constant is None:
            self.model = LogisticRegression(
                C=c_value,
                class_weight="balanced",
                max_iter=2000,
                random_state=RANDOM_STATE,
                solver="liblinear",
            )
            self.model.fit(self.scaler.transform(matrix), labels)

    def probability(self, candidates: list[Panel]) -> np.ndarray:
        if self.constant is not None:
            return np.full(len(candidates), self.constant)
        assert self.model is not None
        matrix = self.scaler.transform(
            self.vectorizer.transform([support_features(row) for row in candidates])
        )
        return self.model.predict_proba(matrix)[:, 1]


def study_macro(values: list[tuple[str, float]]) -> float:
    grouped: dict[str, list[float]] = defaultdict(list)
    for study, value in values:
        grouped[study].append(value)
    return float(np.mean([np.mean(group) for group in grouped.values()]))


def select_c(train: list[Panel]) -> tuple[float, dict[str, dict[str, float]]]:
    studies = sorted({row.study for row in train})
    folds = {index: [] for index in range(5)}
    for study in studies:
        index = int(hashlib.sha256(study.encode()).hexdigest(), 16) % 5
        folds[index].append(study)
    scores: dict[str, dict[str, float]] = {}
    for c_value in CS:
        regrets = []
        probabilities = []
        labels = []
        for validation_studies in folds.values():
            if not validation_studies:
                continue
            validation_set = set(validation_studies)
            inner_train = [row for row in train if row.study not in validation_set]
            validation = [row for row in train if row.study in validation_set]
            gate = Gate(inner_train, c_value)
            probability = gate.probability(validation)
            for row, value in zip(validation, probability, strict=True):
                condition = HISTORY if value >= 0.5 else ZERO
                regret = float(condition_metrics(row, condition)["normalized_regret"])
                regrets.append((row.study, regret))
                probabilities.append(float(value))
                labels.append(history_helped(row))
        scores[str(c_value)] = {
            "study_macro_routed_regret": study_macro(regrets),
            "brier_score": float(np.mean((np.asarray(probabilities) - labels) ** 2)),
        }
    selected = min(
        CS,
        key=lambda value: (
            scores[str(value)]["study_macro_routed_regret"],
            scores[str(value)]["brier_score"],
            value,
        ),
    )
    return selected, scores


def predict() -> dict[str, Any]:
    panels = load_panels()
    studies = sorted({row.study for row in panels})
    rows = []
    fits = []
    for heldout in studies:
        train = open_training_labels([row for row in panels if row.study != heldout])
        test = [row for row in panels if row.study == heldout]
        selected_c, inner_scores = select_c(train)
        gate = Gate(train, selected_c)
        probabilities = gate.probability(test)
        fits.append(
            {
                "heldout_study": heldout,
                "selected_C": selected_c,
                "inner_scores": inner_scores,
                "train_studies": len({row.study for row in train}),
                "train_panels": len(train),
                "test_panels": len(test),
            }
        )
        for panel, probability in zip(test, probabilities, strict=True):
            condition = HISTORY if probability >= 0.5 else ZERO
            selected = panel.history_prediction if condition == HISTORY else panel.zero_prediction
            uncertain = abs(float(probability) - 0.5) <= ABSTENTION_MARGIN
            forecast_abstained = bool(selected["prediction"]["abstain"])
            rows.append(
                {
                    "heldout_study": panel.study,
                    "target_panel": panel.panel,
                    "domain": panel.domain,
                    "history_support_probability": float(probability),
                    "selected_condition": condition,
                    "abstain": uncertain or forecast_abstained,
                    "abstention_reason": (
                        "uncertain_history_support"
                        if uncertain
                        else "selected_forecast_abstained"
                        if forecast_abstained
                        else None
                    ),
                    "prediction": selected["prediction"],
                    "usage": {
                        "zero_history": panel.zero_prediction["usage"],
                        "retrieved_history": (
                            panel.history_prediction["usage"] if condition == HISTORY else None
                        ),
                    },
                }
            )
    PREDICTIONS.write_text("".join(canonical(row) + "\n" for row in rows))
    receipt = {
        "artifact": "anarres_history_support_gate_fit_receipt_v1",
        "status": "outer predictions written before protected outcome scoring",
        "contract_sha256": sha256(CONTRACT),
        "base_predictions_sha256": sha256(BASE_PREDICTIONS),
        "predictions": {"rows": len(rows), "sha256": sha256(PREDICTIONS)},
        "fits": fits,
    }
    FITS.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def summarize_route(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_study: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_study[row["heldout_study"]].append(row)
    metrics = ("normalized_regret", "pairwise_ordering", "top_choice_credit")
    summary = {
        "studies": len(by_study),
        "panels": len(rows),
        "coverage": float(np.mean([not row["abstain"] for row in rows])),
        **{
            f"study_macro_{metric}": float(
                np.mean([np.mean([row[metric] for row in group]) for group in by_study.values()])
            )
            for metric in metrics
        },
    }
    selective = {
        study: [row for row in group if not row["abstain"]] for study, group in by_study.items()
    }
    selective = {study: group for study, group in selective.items() if group}
    summary["selective_studies"] = len(selective)
    summary["selective_study_macro_regret"] = (
        float(
            np.mean(
                [
                    np.mean([row["normalized_regret"] for row in group])
                    for group in selective.values()
                ]
            )
        )
        if selective
        else None
    )
    return summary


def usage_total(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = {"requests": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for row in rows:
        usages = [value for value in row["usage"].values() if value is not None]
        totals["requests"] += len(usages)
        for usage in usages:
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                totals[field] += int(usage[field])
    return totals


def score(receipt: dict[str, Any] | None = None) -> dict[str, Any]:
    if receipt is None:
        receipt = json.loads(FITS.read_text())
    if receipt["contract_sha256"] != sha256(CONTRACT):
        raise ValueError("history-gate contract changed after fitting")
    if receipt["predictions"]["sha256"] != sha256(PREDICTIONS):
        raise ValueError("history-gate prediction digest mismatch")
    label_by_panel = {}
    for row in read_jsonl(LABELS):
        label_by_panel[(row["heldout_study"], row["target_panel"])] = row
    base_panels = {(row.study, row.panel): row for row in load_panels()}
    learned_rows = []
    probabilities = []
    benefit_labels = []
    for row in read_jsonl(PREDICTIONS):
        key = (row["heldout_study"], row["target_panel"])
        label = label_by_panel[key]
        panel = replace(base_panels[key], label=label)
        metrics = SCORER.panel_metrics(row["prediction"], label)
        learned_rows.append({**row, **metrics, "abstain": row["abstain"]})
        probabilities.append(float(row["history_support_probability"]))
        benefit_labels.append(history_helped(panel))

    comparator_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, panel in base_panels.items():
        panel = replace(panel, label=label_by_panel[key])
        for name, condition in (
            ("measurement_only", ZERO),
            ("always_retrieve", HISTORY),
            (
                "frozen_domain_route",
                HISTORY if panel.domain in {"agentic_coding", "finance", "robotics"} else ZERO,
            ),
        ):
            prediction = panel.history_prediction if condition == HISTORY else panel.zero_prediction
            metrics = SCORER.panel_metrics(prediction["prediction"], panel.label)
            forced_abstain = name == "frozen_domain_route" and panel.domain == "legal"
            comparator_rows[name].append(
                {
                    "heldout_study": panel.study,
                    "target_panel": panel.panel,
                    "abstain": forced_abstain or bool(prediction["prediction"]["abstain"]),
                    "usage": {"selected_forecast": prediction["usage"]},
                    **metrics,
                }
            )
    summaries = {name: summarize_route(rows) for name, rows in comparator_rows.items()}
    summaries["learned_history_gate"] = summarize_route(learned_rows)
    brier = float(
        np.mean((np.asarray(probabilities) - np.asarray(benefit_labels, dtype=float)) ** 2)
    )
    auc = (
        float(roc_auc_score(benefit_labels, probabilities))
        if len(set(benefit_labels)) == 2
        else None
    )
    result = {
        "artifact": "anarres_history_support_gate_results_v1",
        "evidence_tier": "retrospective development-selected complete-study replay",
        "inputs": {
            "contract_sha256": sha256(CONTRACT),
            "base_predictions_sha256": sha256(BASE_PREDICTIONS),
            "base_prediction_receipt_sha256": sha256(BASE_RECEIPT),
            "protected_labels_sha256": sha256(LABELS),
            "predictions_sha256": sha256(PREDICTIONS),
            "fit_receipt_sha256": sha256(FITS),
        },
        "routes": summaries,
        "history_support_calibration": {
            "panels": len(probabilities),
            "history_helped_panels": int(sum(benefit_labels)),
            "brier_score": brier,
            "roc_auc": auc,
        },
        "route_inference": {
            **{name: usage_total(rows) for name, rows in comparator_rows.items()},
            "learned_history_gate": usage_total(learned_rows),
        },
        "comparison_with_frozen_domain_route": {
            "regret_improvement": (
                summaries["frozen_domain_route"]["study_macro_normalized_regret"]
                - summaries["learned_history_gate"]["study_macro_normalized_regret"]
            ),
            "ordering_improvement": (
                summaries["learned_history_gate"]["study_macro_pairwise_ordering"]
                - summaries["frozen_domain_route"]["study_macro_pairwise_ordering"]
            ),
            "coverage_change": (
                summaries["learned_history_gate"]["coverage"]
                - summaries["frozen_domain_route"]["coverage"]
            ),
            "selective_regret_change": (
                summaries["learned_history_gate"]["selective_study_macro_regret"]
                - summaries["frozen_domain_route"]["selective_study_macro_regret"]
            ),
        },
        "advancement_gate": {
            "independent_prospective_test": False,
            "retain_starting_policy_scored": False,
            "total_research_cost_scored": False,
            "passed": False,
            "decision": "freeze only as a candidate for a new prospective comparison",
        },
        "claim_boundary": (
            "The feature set was informed by an outcome-aware feasibility analysis on this "
            "development replay. Nested complete-study scoring measures the frozen fitting "
            "procedure, not an independent prospective test."
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
