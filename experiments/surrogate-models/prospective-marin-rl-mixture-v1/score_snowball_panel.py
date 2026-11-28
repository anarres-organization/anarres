#!/usr/bin/env python3
"""Score frozen Snowball candidate forecasts after every outcome is released."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from itertools import combinations
from pathlib import Path
from statistics import mean


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_finite(value: object, name: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def interval(values: list[float]) -> list[float]:
    return [percentile(values, 0.025), percentile(values, 0.975)]


def pairwise_credit(
    predicted_left: float, predicted_right: float, observed_left: float, observed_right: float
) -> float:
    predicted = (predicted_left > predicted_right) - (predicted_left < predicted_right)
    observed = (observed_left > observed_right) - (observed_left < observed_right)
    if predicted == 0 or observed == 0:
        return 0.5
    return float(predicted == observed)


def roc_auc(labels: list[bool], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores, strict=True) if label]
    negatives = [score for label, score in zip(labels, scores, strict=True) if not label]
    if not positives or not negatives:
        return None
    credit = 0.0
    for positive in positives:
        for negative in negatives:
            credit += float(positive > negative) + 0.5 * float(positive == negative)
    return credit / (len(positives) * len(negatives))


def average_precision(labels: list[bool], scores: list[float]) -> float | None:
    positives = sum(labels)
    if positives == 0:
        return None
    thresholds = sorted(set(scores), reverse=True)
    prior_recall = 0.0
    result = 0.0
    for threshold in thresholds:
        selected = [index for index, score in enumerate(scores) if score >= threshold]
        true_positives = sum(labels[index] for index in selected)
        recall = true_positives / positives
        precision = true_positives / len(selected)
        result += (recall - prior_recall) * precision
        prior_recall = recall
    return result


def validate_contract(contract: dict) -> tuple[list[str], list[str]]:
    if contract.get("status") != "FROZEN_BEFORE_CANDIDATE_OUTCOMES":
        raise ValueError("scoring contract was not frozen before candidate outcomes")
    if contract.get("candidate_outcomes_opened") is not False:
        raise ValueError("scoring contract must state that candidate outcomes were unopened")
    candidates = contract["candidate_ids"]
    targets = contract["target_ids"]
    if not candidates or not targets:
        raise ValueError("candidate and target identities must be non-empty")
    if len(candidates) != len(set(candidates)) or len(targets) != len(set(targets)):
        raise ValueError("candidate and target identities must be unique")
    seeds = contract["replicate_seeds"]
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("replicate seeds must be non-empty and unique")
    uncertainty = contract["uncertainty"]
    if not isinstance(uncertainty["resamples"], int) or uncertainty["resamples"] <= 0:
        raise ValueError("uncertainty resamples must be a positive integer")
    token_budget = contract["generated_token_budget_per_intervention"]
    token_tolerance = contract["generated_token_tolerance"]
    if not isinstance(token_budget, int) or token_budget <= 0:
        raise ValueError("generated-token budget must be a positive integer")
    if not isinstance(token_tolerance, int) or token_tolerance < 0:
        raise ValueError("generated-token tolerance must be a non-negative integer")
    weights = contract["target_weights"]
    margins = contract["regression_margins"]
    if set(weights) != set(targets) or set(margins) != set(targets):
        raise ValueError("target weights and regression margins must cover the frozen targets")
    numeric_weights = [require_finite(weights[target], f"weight {target}") for target in targets]
    if any(weight < 0 for weight in numeric_weights):
        raise ValueError("target weights must be non-negative")
    if not math.isclose(sum(numeric_weights), 1.0):
        raise ValueError("target weights must sum to one")
    if any(require_finite(margins[target], f"margin {target}") < 0 for target in targets):
        raise ValueError("regression margins must be non-negative")
    return candidates, targets


def validate_predictions(
    predictions: dict, contract: dict, candidates: list[str], targets: list[str]
) -> dict[str, dict]:
    if predictions.get("study_id") != contract["study_id"]:
        raise ValueError("prediction receipt belongs to a different study")
    if predictions.get("protected_outcomes_opened") is not False:
        raise ValueError("prediction receipt must predate protected outcomes")
    candidate_rows = predictions["candidates"]
    rows = {row["candidate_id"]: row for row in candidate_rows}
    if (
        set(rows) != set(candidates)
        or len(rows) != len(candidates)
        or len(candidate_rows) != len(candidates)
    ):
        raise ValueError("prediction receipt does not cover the frozen candidates exactly")
    for candidate_id, row in rows.items():
        if not isinstance(row.get("abstain"), bool):
            raise ValueError(f"prediction for {candidate_id} must declare abstention")
        target_rows = row["targets"]
        if set(target_rows) != set(targets):
            raise ValueError(f"prediction for {candidate_id} does not cover every target")
        for target in targets:
            prediction = target_rows[target]
            change = require_finite(
                prediction["change"], f"predicted change {candidate_id}/{target}"
            )
            lower = require_finite(
                prediction["interval"][0], f"lower interval {candidate_id}/{target}"
            )
            upper = require_finite(
                prediction["interval"][1], f"upper interval {candidate_id}/{target}"
            )
            risk = require_finite(
                prediction["regression_probability"],
                f"regression probability {candidate_id}/{target}",
            )
            if lower > change or change > upper:
                raise ValueError(
                    f"prediction interval does not contain its estimate for {candidate_id}/{target}"
                )
            if lower < -1 or upper > 1:
                raise ValueError(
                    f"prediction interval lies outside [-1, 1] for {candidate_id}/{target}"
                )
            if not 0 <= risk <= 1:
                raise ValueError(
                    f"regression probability lies outside [0, 1] for {candidate_id}/{target}"
                )
    return rows


def validate_outcomes(
    outcomes: dict, contract: dict, candidates: list[str], targets: list[str]
) -> dict[str, dict]:
    if outcomes.get("study_id") != contract["study_id"]:
        raise ValueError("outcomes belong to a different study")
    if outcomes.get("status") != "COMPLETE_RELEASE_GATE_PASSED":
        raise ValueError("outcomes cannot be scored before the complete release gate passes")
    starting = outcomes["starting_policy_targets"]
    if set(starting) != set(targets):
        raise ValueError("starting-policy outcomes do not cover the frozen targets")
    for target in targets:
        value = require_finite(starting[target], f"starting outcome {target}")
        if not 0 <= value <= 1:
            raise ValueError(f"starting outcome lies outside [0, 1] for {target}")
    for field in ("measurement_accelerator_hours", "starting_evaluation_accelerator_hours"):
        if require_finite(outcomes["cost"][field], field) < 0:
            raise ValueError(f"{field} must be non-negative")
    candidate_rows = outcomes["candidates"]
    rows = {row["candidate_id"]: row for row in candidate_rows}
    if (
        set(rows) != set(candidates)
        or len(rows) != len(candidates)
        or len(candidate_rows) != len(candidates)
    ):
        raise ValueError("outcomes do not cover the frozen candidates exactly")
    expected_seeds = contract["replicate_seeds"]
    for candidate_id, row in rows.items():
        by_seed = {seed_row["seed"]: seed_row for seed_row in row["seeds"]}
        if (
            set(by_seed) != set(expected_seeds)
            or len(by_seed) != len(expected_seeds)
            or len(row["seeds"]) != len(expected_seeds)
        ):
            raise ValueError(f"outcomes for {candidate_id} do not cover the frozen seeds")
        for seed, seed_row in by_seed.items():
            generated_tokens = seed_row["generated_tokens"]
            if not isinstance(generated_tokens, int) or generated_tokens < 0:
                raise ValueError(
                    f"generated tokens must be a non-negative integer for {candidate_id}/{seed}"
                )
            if (
                abs(generated_tokens - contract["generated_token_budget_per_intervention"])
                > contract["generated_token_tolerance"]
            ):
                raise ValueError(f"generated-token budget differs for {candidate_id}/{seed}")
            for field in ("training_accelerator_hours", "evaluation_accelerator_hours"):
                if require_finite(seed_row[field], f"{field} {candidate_id}/{seed}") < 0:
                    raise ValueError(f"{field} must be non-negative for {candidate_id}/{seed}")
            if set(seed_row["targets"]) != set(targets):
                raise ValueError(f"outcomes for {candidate_id}/{seed} do not cover every target")
            for target in targets:
                value = require_finite(
                    seed_row["targets"][target], f"outcome {candidate_id}/{seed}/{target}"
                )
                if not 0 <= value <= 1:
                    raise ValueError(
                        f"outcome lies outside [0, 1] for {candidate_id}/{seed}/{target}"
                    )
    return rows


def select_candidate(predicted: dict[str, float], abstained: set[str]) -> str:
    eligible = {"retain_starting_policy": 0.0}
    eligible.update(
        {candidate: value for candidate, value in predicted.items() if candidate not in abstained}
    )
    return min(
        eligible,
        key=lambda candidate: (
            -eligible[candidate],
            candidate != "retain_starting_policy",
            candidate,
        ),
    )


def score(contract: dict, predictions: dict, outcomes: dict) -> dict:
    candidates, targets = validate_contract(contract)
    predicted_rows = validate_predictions(predictions, contract, candidates, targets)
    outcome_rows = validate_outcomes(outcomes, contract, candidates, targets)
    weights = contract["target_weights"]
    margins = contract["regression_margins"]
    seeds = contract["replicate_seeds"]
    starting = outcomes["starting_policy_targets"]

    predicted_changes: dict[str, dict[str, float]] = {}
    observed_seed_changes: dict[str, dict[int, dict[str, float]]] = {}
    for candidate in candidates:
        predicted_changes[candidate] = {
            target: float(predicted_rows[candidate]["targets"][target]["change"])
            for target in targets
        }
        by_seed = {row["seed"]: row for row in outcome_rows[candidate]["seeds"]}
        observed_seed_changes[candidate] = {
            seed: {
                target: float(by_seed[seed]["targets"][target]) - float(starting[target])
                for target in targets
            }
            for seed in seeds
        }

    observed_changes = {
        candidate: {
            target: mean(observed_seed_changes[candidate][seed][target] for seed in seeds)
            for target in targets
        }
        for candidate in candidates
    }
    predicted_utility = {
        candidate: sum(weights[target] * predicted_changes[candidate][target] for target in targets)
        for candidate in candidates
    }
    observed_seed_utility = {
        candidate: {
            seed: sum(
                weights[target] * observed_seed_changes[candidate][seed][target]
                for target in targets
            )
            for seed in seeds
        }
        for candidate in candidates
    }
    observed_utility = {
        candidate: mean(observed_seed_utility[candidate].values()) for candidate in candidates
    }
    abstained = {candidate for candidate in candidates if predicted_rows[candidate]["abstain"]}
    selected = select_candidate(predicted_utility, abstained)
    observed_with_retain = {"retain_starting_policy": 0.0, **observed_utility}
    predicted_with_retain = {"retain_starting_policy": 0.0, **predicted_utility}
    regret = max(observed_with_retain.values()) - observed_with_retain[selected]
    best_observed = max(observed_with_retain.values())

    pairs = []
    for left, right in combinations(["retain_starting_policy", *candidates], 2):
        pairs.append(
            {
                "left": left,
                "right": right,
                "credit": pairwise_credit(
                    predicted_with_retain[left],
                    predicted_with_retain[right],
                    observed_with_retain[left],
                    observed_with_retain[right],
                ),
            }
        )

    target_rows = []
    squared_errors = []
    accepted_squared_errors = []
    labels = []
    risks = []
    interval_hits = []
    for candidate in candidates:
        for target in targets:
            prediction = predicted_rows[candidate]["targets"][target]
            predicted_change = predicted_changes[candidate][target]
            observed_change = observed_changes[candidate][target]
            label = observed_change < -float(margins[target])
            lower, upper = prediction["interval"]
            hit = float(lower) <= observed_change <= float(upper)
            squared_errors.append((predicted_change - observed_change) ** 2)
            if candidate not in abstained:
                accepted_squared_errors.append((predicted_change - observed_change) ** 2)
            labels.append(label)
            risks.append(float(prediction["regression_probability"]))
            interval_hits.append(hit)
            target_rows.append(
                {
                    "candidate_id": candidate,
                    "target": target,
                    "predicted_change": predicted_change,
                    "observed_change": observed_change,
                    "regression_probability": float(prediction["regression_probability"]),
                    "observed_regression": label,
                    "interval_covered": hit,
                }
            )

    ordered_risk = sorted(
        target_rows,
        key=lambda row: (-row["regression_probability"], row["candidate_id"], row["target"]),
    )
    top_count = max(1, math.ceil(0.2 * len(ordered_risk)))
    regressions = sum(labels)
    top_regressions = sum(row["observed_regression"] for row in ordered_risk[:top_count])

    random_generator = random.Random(contract["uncertainty"]["random_seed"])
    bootstrap_regret = []
    for _ in range(contract["uncertainty"]["resamples"]):
        sampled = [random_generator.choice(seeds) for _ in seeds]
        sampled_utility = {
            candidate: mean(observed_seed_utility[candidate][seed] for seed in sampled)
            for candidate in candidates
        }
        sampled_with_retain = {"retain_starting_policy": 0.0, **sampled_utility}
        bootstrap_regret.append(max(sampled_with_retain.values()) - sampled_with_retain[selected])

    candidate_cost = {
        candidate: {
            "training_accelerator_hours": sum(
                float(row["training_accelerator_hours"]) for row in outcome_rows[candidate]["seeds"]
            ),
            "evaluation_accelerator_hours": sum(
                float(row["evaluation_accelerator_hours"])
                for row in outcome_rows[candidate]["seeds"]
            ),
        }
        for candidate in candidates
    }
    total_cost = (
        float(outcomes["cost"]["measurement_accelerator_hours"])
        + float(outcomes["cost"]["starting_evaluation_accelerator_hours"])
        + sum(
            values["training_accelerator_hours"] + values["evaluation_accelerator_hours"]
            for values in candidate_cost.values()
        )
    )

    return {
        "schema_version": "anarres.snowball-panel-score.v1",
        "study_id": contract["study_id"],
        "status": "CANDIDATE_OUTCOMES_RELEASED_AND_SCORED",
        "selected_candidate": selected,
        "observed_best_candidates": sorted(
            candidate for candidate, value in observed_with_retain.items() if value == best_observed
        ),
        "abstained_candidates": sorted(abstained),
        "candidate_prediction_coverage": (len(candidates) - len(abstained)) / len(candidates),
        "predicted_utility": predicted_with_retain,
        "observed_utility": observed_with_retain,
        "observed_seed_utility": observed_seed_utility,
        "aggregate_utility_rmse": math.sqrt(
            mean(
                (predicted_utility[candidate] - observed_utility[candidate]) ** 2
                for candidate in candidates
            )
        ),
        "allocation_regret": regret,
        "allocation_regret_95_interval": interval(bootstrap_regret),
        "pairwise_ordering_accuracy": mean(row["credit"] for row in pairs),
        "pairwise_comparisons": pairs,
        "target_change_rmse": math.sqrt(mean(squared_errors)),
        "accepted_target_change_rmse": (
            math.sqrt(mean(accepted_squared_errors)) if accepted_squared_errors else None
        ),
        "target_interval_coverage": mean(interval_hits),
        "regression": {
            "observed": regressions,
            "roc_auc": roc_auc(labels, risks),
            "average_precision": average_precision(labels, risks),
            "brier_score": mean(
                (risk - float(label)) ** 2 for risk, label in zip(risks, labels, strict=True)
            ),
            "top_risk_20_percent_rows": top_count,
            "recall_in_top_risk_20_percent": top_regressions / regressions if regressions else None,
        },
        "cost": {
            "measurement_accelerator_hours": float(
                outcomes["cost"]["measurement_accelerator_hours"]
            ),
            "starting_evaluation_accelerator_hours": float(
                outcomes["cost"]["starting_evaluation_accelerator_hours"]
            ),
            "candidate_accelerator_hours": candidate_cost,
            "total_accelerator_hours": total_cost,
            "utility_cost_conversion": None,
        },
        "candidate_targets": target_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)

    contract = json.loads(arguments.contract.read_text(encoding="utf-8"))
    predictions = json.loads(arguments.predictions.read_text(encoding="utf-8"))
    outcomes = json.loads(arguments.outcomes.read_text(encoding="utf-8"))
    bound = contract.get("bound_inputs", {})
    if bound.get("score_snowball_panel_sha256") != sha256(Path(__file__)):
        raise ValueError("scoring implementation differs from the frozen contract")
    if bound.get("prediction_receipt_sha256") != sha256(arguments.predictions):
        raise ValueError("prediction receipt differs from the frozen contract")

    result = score(contract, predictions, outcomes)
    result["inputs"] = {
        "contract_sha256": sha256(arguments.contract),
        "prediction_receipt_sha256": sha256(arguments.predictions),
        "outcomes_sha256": sha256(arguments.outcomes),
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
