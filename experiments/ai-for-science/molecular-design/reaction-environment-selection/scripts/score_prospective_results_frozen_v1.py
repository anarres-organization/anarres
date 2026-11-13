#!/usr/bin/env python3
"""Score the frozen two-bank molecular prospective decision after release."""

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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def panel_name(arm: str, seed: int, step: int) -> str:
    return f"{arm}-{seed}-step{step:06d}"


def score(
    contract_path: Path,
    development_path: Path,
    freeze_path: Path,
    gate_path: Path,
    panels_root: Path,
) -> dict[str, Any]:
    contract = load(contract_path)
    development = load(development_path)
    frozen = load(freeze_path)
    gate = load(gate_path)
    if frozen.get("prospective_outcomes_opened") is not False:
        raise ValueError("forecast freeze must precede prospective outcomes")
    if frozen.get("inputs", {}).get("scoring_implementation_sha256") != sha256(Path(__file__)):
        raise ValueError("scoring implementation differs from the frozen forecast")
    if frozen.get("inputs", {}).get("contract_sha256") != sha256(contract_path):
        raise ValueError("forecast is not bound to the matched contract")
    if frozen.get("inputs", {}).get("development_results_sha256") != sha256(development_path):
        raise ValueError("development results differ from the forecast freeze")
    if (
        gate.get("comparative_scoring_authorized") is not True
        or gate.get("panel_kind") != "prospective"
        or gate.get("contract_sha256") != sha256(contract_path)
    ):
        raise ValueError("prospective endpoint gate did not authorize scoring")

    banks = list(contract["development_panel"]["prospective_banks_excluded"])
    seeds = list(contract["training"]["seeds"])
    steps = list(contract["training"]["checkpoint_updates"])
    budgets = list(contract["training"]["target_oracle_attempt_budgets"])
    attempts = int(contract["evaluation"]["attempts_per_policy_seed_checkpoint"])
    gate_records = {
        (row["arm"], row["training_seed"], row["checkpoint_step"]): row for row in gate["records"]
    }
    warm = {
        int(row["training_seed"]): float(row["warm_start_rate"])
        for row in development["seed_records"]
    }
    if set(warm) != set(seeds):
        raise ValueError("development record does not contain both warm-start rates")

    seed_records = []
    report_hashes = {}
    for bank in banks:
        for seed in seeds:
            for step, budget in zip(steps, budgets, strict=True):
                identity = (bank, seed, step)
                if identity not in gate_records:
                    raise ValueError(f"prospective endpoint gate is missing {identity}")
                report_path = panels_root / panel_name(*identity) / "QUALIFYING_HITS.json"
                report = load(report_path)
                if sha256(report_path) != gate_records[identity]["qualifying_report_sha256"]:
                    raise ValueError(f"qualifying report differs from endpoint gate: {identity}")
                if (
                    report.get("status") != "complete"
                    or report.get("attempts") != attempts
                    or report.get("infrastructure_failures") != 0
                ):
                    raise ValueError(f"qualifying report is incomplete or invalid: {identity}")
                rate = report.get("unique_qualifying_hit_rate")
                if not isinstance(rate, (int, float)) or isinstance(rate, bool):
                    raise ValueError(f"qualifying-hit rate is invalid: {identity}")
                seed_records.append(
                    {
                        "bank": bank,
                        "training_seed": seed,
                        "checkpoint_step": step,
                        "target_oracle_attempt_budget": budget,
                        "unique_qualifying_hit_rate": float(rate),
                        "warm_start_rate": warm[seed],
                        "utility": float(rate) - warm[seed],
                    }
                )
                report_hashes[panel_name(*identity)] = sha256(report_path)

    means = {
        (bank, budget): mean(
            row["utility"]
            for row in seed_records
            if row["bank"] == bank and row["target_oracle_attempt_budget"] == budget
        )
        for bank in banks
        for budget in budgets
    }
    decisions = []
    for frozen_decision in frozen["decisions"]:
        budget = int(frozen_decision["target_oracle_attempt_budget"])
        observed_winner = max(banks, key=lambda bank: (means[(bank, budget)], bank))
        predicted_winner = frozen_decision["predicted_winner"]
        best = means[(observed_winner, budget)]
        regret = best - means[(predicted_winner, budget)]
        seed_winners = {
            str(seed): max(
                banks,
                key=lambda bank: (
                    next(
                        row["utility"]
                        for row in seed_records
                        if row["bank"] == bank
                        and row["training_seed"] == seed
                        and row["target_oracle_attempt_budget"] == budget
                    ),
                    bank,
                ),
            )
            for seed in seeds
        }
        decisions.append(
            {
                **frozen_decision,
                "observed_winner": observed_winner,
                "observed_margin": abs(means[(banks[0], budget)] - means[(banks[1], budget)]),
                "point_prediction_correct": predicted_winner == observed_winner,
                "point_prediction_regret": regret,
                "decision_issued": not frozen_decision["abstain"],
                "seed_winners": seed_winners,
                "seed_winner_agreement": len(set(seed_winners.values())) == 1,
            }
        )

    model_scores = {}
    for model_name, model_forecasts in frozen["forecasts"].items():
        errors = []
        ordering_credit = []
        for budget in budgets:
            predicted = {
                bank: next(
                    row["predicted_utility"]
                    for row in model_forecasts[bank]
                    if row["target_oracle_attempt_budget"] == budget
                )
                for bank in banks
            }
            for bank in banks:
                errors.append(predicted[bank] - means[(bank, budget)])
            observed_difference = means[(banks[0], budget)] - means[(banks[1], budget)]
            predicted_difference = predicted[banks[0]] - predicted[banks[1]]
            ordering_credit.append(
                0.5
                if observed_difference == 0 or predicted_difference == 0
                else float(observed_difference * predicted_difference > 0)
            )
        model_scores[model_name] = {
            "curve_rmse": math.sqrt(mean(error * error for error in errors)),
            "pairwise_ordering": mean(ordering_credit),
        }

    return {
        "schema_version": "anarres.molecular-prospective-results.v1",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "PROSPECTIVE_OUTCOMES_RELEASED_AND_SCORED",
        "prospective_outcomes_opened": True,
        "seed_records": seed_records,
        "mean_utilities": {
            bank: {str(budget): means[(bank, budget)] for budget in budgets} for bank in banks
        },
        "decisions": decisions,
        "model_scores": model_scores,
        "issued_decision_mean_regret": (
            mean(row["point_prediction_regret"] for row in decisions if row["decision_issued"])
            if any(row["decision_issued"] for row in decisions)
            else None
        ),
        "inputs": {
            "contract_sha256": sha256(contract_path),
            "development_results_sha256": sha256(development_path),
            "forecast_freeze_sha256": sha256(freeze_path),
            "endpoint_gate_sha256": sha256(gate_path),
            "qualifying_reports": dict(sorted(report_hashes.items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--development-results", type=Path, required=True)
    parser.add_argument("--forecast-freeze", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--panels-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    payload = score(
        args.contract,
        args.development_results,
        args.forecast_freeze,
        args.gate,
        args.panels_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": payload["status"], "decisions": payload["decisions"]}, indent=2))


if __name__ == "__main__":
    main()
