#!/usr/bin/env python3
"""Fit development predictors and freeze the two-bank prospective decision."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
DEFAULT_PROSPECTIVE_CONTRACT = ROOT / "PROSPECTIVE_BANK_CONSTRUCTION_CONTRACT_V1.json"
DEFAULT_SCORER = Path(__file__).with_name("score_prospective_results.py")
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
OPERATIONAL = (
    "mean_target_reward",
    "mean_generated_action_count",
    "mean_oracle_seconds",
)
GRAPH = (
    *OPERATIONAL,
    "unique_scaffold_fraction",
    "unique_ring_systems_per_record",
    "unique_route_fraction",
    "unique_reaction_families",
    "embedding_mean_nearest_neighbor_distance",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def solve(matrix: list[list[float]], target: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, target, strict=True)]
    for column in range(len(augmented)):
        pivot = max(range(column, len(augmented)), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("singular ridge system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(len(augmented)):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                left - factor * right
                for left, right in zip(augmented[row], augmented[column], strict=True)
            ]
    return [row[-1] for row in augmented]


def fit_ridge(matrix: list[list[float]], target: list[float], alpha: float) -> list[float]:
    width = len(matrix[0])
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for row, outcome in zip(matrix, target, strict=True):
        for left in range(width):
            rhs[left] += row[left] * outcome
            for right in range(width):
                gram[left][right] += row[left] * row[right]
    for index in range(width):
        gram[index][index] += alpha
    return solve(gram, rhs)


def prediction(row: list[float], coefficients: list[float]) -> float:
    return sum(left * right for left, right in zip(row, coefficients, strict=True))


def standardizers(
    coordinates: dict[str, dict[str, float]], arms: list[str], features: tuple[str, ...]
) -> dict[str, dict[str, float]]:
    result = {}
    for feature in features:
        values = [float(coordinates[arm][feature]) for arm in arms]
        center = mean(values)
        scale = math.sqrt(mean((value - center) ** 2 for value in values)) or 1.0
        result[feature] = {"mean": center, "scale": scale}
    return result


def row(
    coordinates: dict[str, float],
    budget_index: int,
    budgets: list[int],
    features: tuple[str, ...],
    state: dict[str, dict[str, float]],
) -> list[float]:
    return [float(index == budget_index) for index in range(len(budgets))] + [
        (float(coordinates[feature]) - state[feature]["mean"]) / state[feature]["scale"]
        for feature in features
    ]


def fit_model(
    development: dict[str, Any], features: tuple[str, ...]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    coordinates = development["measurement_coordinates"]
    arms = sorted(coordinates)
    curves = development["mean_utility_curves"]
    budgets = sorted({int(item["target_oracle_attempt_budget"]) for item in curves})
    by_arm_budget = {
        (item["arm"], int(item["target_oracle_attempt_budget"])): float(item["mean_utility"])
        for item in curves
    }
    candidates = []
    for alpha in ALPHAS:
        residuals = []
        for held_out in arms:
            train_arms = [arm for arm in arms if arm != held_out]
            state = standardizers(coordinates, train_arms, features)
            train_x = []
            train_y = []
            for arm in train_arms:
                for budget_index, budget in enumerate(budgets):
                    train_x.append(row(coordinates[arm], budget_index, budgets, features, state))
                    train_y.append(by_arm_budget[(arm, budget)])
            coefficients = fit_ridge(train_x, train_y, alpha)
            for budget_index, budget in enumerate(budgets):
                estimate = prediction(
                    row(coordinates[held_out], budget_index, budgets, features, state),
                    coefficients,
                )
                residuals.append(estimate - by_arm_budget[(held_out, budget)])
        candidates.append((math.sqrt(mean(value * value for value in residuals)), alpha, residuals))
    rmse, alpha, residuals = min(candidates, key=lambda item: (item[0], item[1]))
    state = standardizers(coordinates, arms, features)
    matrix = []
    target = []
    for arm in arms:
        for budget_index, budget in enumerate(budgets):
            matrix.append(row(coordinates[arm], budget_index, budgets, features, state))
            target.append(by_arm_budget[(arm, budget)])
    coefficients = fit_ridge(matrix, target, alpha)
    return (
        {
            "features": list(features),
            "budgets": budgets,
            "alpha": alpha,
            "coefficients": coefficients,
            "standardizers": state,
            "leave_one_arm_out_rmse": rmse,
            "empirical_uncertainty_half_width": max(abs(value) for value in residuals),
            "form": "budget intercepts plus standardized measurement coordinates with ridge",
        },
        [
            {"arm": arm, "budget": budget, "observed_utility": by_arm_budget[(arm, budget)]}
            for arm in arms
            for budget in budgets
        ],
    )


def validate_prospective_banks(
    payload: dict[str, Any], contract: dict[str, Any], prospective_contract_path: Path
) -> None:
    if payload.get("qualification") != "pass" or payload.get("outcomes_opened") is not False:
        raise ValueError("prospective banks must qualify before any outcomes are opened")
    expected = set(contract["development_panel"]["prospective_banks_excluded"])
    if set(payload.get("banks", {})) != expected:
        raise ValueError("prospective bank identities differ from the matched contract")
    if payload.get("inputs", {}).get("prospective_contract_sha256") != sha256(
        prospective_contract_path
    ):
        raise ValueError("prospective bank construction contract digest mismatch")
    expected_size = int(contract["development_panel"]["bank_size"])
    for bank, record in payload["banks"].items():
        members = record.get("members", [])
        if len(members) != expected_size or len(set(members)) != expected_size:
            raise ValueError(f"prospective bank membership is incomplete: {bank}")
        if set(record.get("coordinates", {})) != set(GRAPH):
            raise ValueError(f"prospective bank coordinates are incomplete: {bank}")


def freeze(
    contract_path: Path,
    prospective_contract_path: Path,
    development_path: Path,
    prospective_banks_path: Path,
    scorer_path: Path,
) -> dict[str, Any]:
    contract = load(contract_path)
    development = load(development_path)
    prospective = load(prospective_banks_path)
    if development.get("prospective_outcomes_opened") is not False:
        raise ValueError("development record must keep prospective outcomes sealed")
    if development.get("contract") != contract.get("contract"):
        raise ValueError("development result belongs to a different contract")
    validate_prospective_banks(prospective, contract, prospective_contract_path)
    operational, _ = fit_model(development, OPERATIONAL)
    graph, _ = fit_model(development, GRAPH)
    models = {"operational": operational, "graph_aware": graph}
    forecasts = {}
    for model_name, model in models.items():
        forecasts[model_name] = {}
        for bank, bank_record in prospective["banks"].items():
            forecasts[model_name][bank] = []
            for budget_index, budget in enumerate(model["budgets"]):
                estimate = prediction(
                    row(
                        bank_record["coordinates"],
                        budget_index,
                        model["budgets"],
                        tuple(model["features"]),
                        model["standardizers"],
                    ),
                    model["coefficients"],
                )
                forecasts[model_name][bank].append(
                    {"target_oracle_attempt_budget": budget, "predicted_utility": estimate}
                )
    banks = sorted(prospective["banks"])
    decisions = []
    half_width = graph["empirical_uncertainty_half_width"]
    for budget_index, budget in enumerate(graph["budgets"]):
        values = {
            bank: forecasts["graph_aware"][bank][budget_index]["predicted_utility"]
            for bank in banks
        }
        winner = max(values, key=lambda bank: (values[bank], bank))
        margin = abs(values[banks[0]] - values[banks[1]])
        decisions.append(
            {
                "target_oracle_attempt_budget": budget,
                "predicted_winner": winner,
                "predicted_margin": margin,
                "abstain": margin <= half_width,
            }
        )
    return {
        "schema_version": "anarres.molecular-prospective-freeze.v1",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "PROSPECTIVE_FORECAST_FROZEN__OUTCOMES_UNOPENED",
        "prospective_outcomes_opened": False,
        "models": models,
        "forecasts": forecasts,
        "decisions": decisions,
        "uncertainty_rule": (
            "abstain when the predicted two-bank margin does not exceed the maximum absolute "
            "leave-one-development-arm residual of the graph-aware model"
        ),
        "bank_membership_sha256": {
            bank: hashlib.sha256(
                ("\n".join(prospective["banks"][bank]["members"]) + "\n").encode()
            ).hexdigest()
            for bank in banks
        },
        "inputs": {
            "contract_sha256": sha256(contract_path),
            "prospective_construction_contract_sha256": sha256(prospective_contract_path),
            "development_results_sha256": sha256(development_path),
            "prospective_banks_sha256": sha256(prospective_banks_path),
            "freeze_implementation_sha256": sha256(Path(__file__)),
            "scoring_implementation_sha256": sha256(scorer_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--prospective-contract", type=Path, default=DEFAULT_PROSPECTIVE_CONTRACT)
    parser.add_argument("--development-results", type=Path, required=True)
    parser.add_argument("--prospective-banks", type=Path, required=True)
    parser.add_argument("--scorer", type=Path, default=DEFAULT_SCORER)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    payload = freeze(
        args.contract,
        args.prospective_contract,
        args.development_results,
        args.prospective_banks,
        args.scorer,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": payload["status"], "decisions": payload["decisions"]}, indent=2))


if __name__ == "__main__":
    main()
