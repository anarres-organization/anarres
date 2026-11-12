#!/usr/bin/env python3
"""Score the complete six-bank molecular development panel after its gate passes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
DEFAULT_BANKS = ROOT / "DEVELOPMENT_BANK_QUALIFICATION_V4.json"


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
    banks_path: Path,
    gate_path: Path,
    panels_root: Path,
) -> dict[str, Any]:
    contract = load(contract_path)
    banks = load(banks_path)
    gate = load(gate_path)
    if gate.get("comparative_scoring_authorized") is not True:
        raise ValueError("endpoint gate did not authorize comparative scoring")
    if gate.get("panel_kind") != "development":
        raise ValueError("development scoring requires a development endpoint gate")
    if gate.get("contract_sha256") != sha256(contract_path):
        raise ValueError("endpoint gate is not bound to the matched contract")
    if banks.get("qualification") != "pass":
        raise ValueError("development banks did not pass qualification")

    arms = list(contract["development_panel"]["arms"])
    seeds = list(contract["training"]["seeds"])
    steps = list(contract["training"]["checkpoint_updates"])
    attempts = int(contract["evaluation"]["attempts_per_policy_seed_checkpoint"])
    gate_records = {
        (row["arm"], row["training_seed"], row["checkpoint_step"]): row for row in gate["records"]
    }

    rates: dict[tuple[str, int, int], float] = {}
    report_hashes = {}
    for arm in ["warm_start", *arms]:
        arm_steps = [0] if arm == "warm_start" else steps
        for seed in seeds:
            for step in arm_steps:
                identity = (arm, seed, step)
                if identity not in gate_records:
                    raise ValueError(f"endpoint gate is missing {identity}")
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
                rates[identity] = float(rate)
                report_hashes[panel_name(*identity)] = sha256(report_path)

    records = []
    for arm in arms:
        for seed in seeds:
            warm_rate = rates[("warm_start", seed, 0)]
            for step, budget in zip(
                steps, contract["training"]["target_oracle_attempt_budgets"], strict=True
            ):
                rate = rates[(arm, seed, step)]
                records.append(
                    {
                        "arm": arm,
                        "training_seed": seed,
                        "checkpoint_step": step,
                        "target_oracle_attempt_budget": budget,
                        "unique_qualifying_hit_rate": rate,
                        "warm_start_rate": warm_rate,
                        "utility": rate - warm_rate,
                    }
                )

    means = []
    for arm in arms:
        for step, budget in zip(
            steps, contract["training"]["target_oracle_attempt_budgets"], strict=True
        ):
            rows = [row for row in records if row["arm"] == arm and row["checkpoint_step"] == step]
            means.append(
                {
                    "arm": arm,
                    "checkpoint_step": step,
                    "target_oracle_attempt_budget": budget,
                    "mean_utility": mean(row["utility"] for row in rows),
                    "seed_utilities": {str(row["training_seed"]): row["utility"] for row in rows},
                }
            )

    return {
        "schema_version": "anarres.molecular-development-results.v1",
        "study": contract["study"],
        "contract": contract["contract"],
        "status": "DEVELOPMENT_OUTCOMES_SCORED__PROSPECTIVE_OUTCOMES_UNOPENED",
        "prospective_outcomes_opened": False,
        "primary_outcome": contract["evaluation"]["primary_outcome"],
        "seed_records": records,
        "mean_utility_curves": means,
        "measurement_coordinates": {
            arm: {
                coordinate: mean(view[arm][coordinate] for view in banks["summaries"])
                for coordinate in banks["summaries"][0][arm]
            }
            for arm in arms
        },
        "inputs": {
            "contract_sha256": sha256(contract_path),
            "bank_qualification_sha256": sha256(banks_path),
            "endpoint_gate_sha256": sha256(gate_path),
            "qualifying_reports": dict(sorted(report_hashes.items())),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--banks", type=Path, default=DEFAULT_BANKS)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--panels-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    payload = score(args.contract, args.banks, args.gate, args.panels_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": payload["status"]}, indent=2))


if __name__ == "__main__":
    main()
