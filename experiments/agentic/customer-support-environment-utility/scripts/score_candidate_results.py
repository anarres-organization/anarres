#!/usr/bin/env python3
"""Score a complete, gated customer-support candidate panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from collections import defaultdict
from itertools import combinations
from pathlib import Path

GATE_SPEC = importlib.util.spec_from_file_location(
    "gate_candidate_results", Path(__file__).with_name("gate_candidate_results.py")
)
GATE_MODULE = importlib.util.module_from_spec(GATE_SPEC)
assert GATE_SPEC.loader is not None
GATE_SPEC.loader.exec_module(GATE_MODULE)
parse_arms = GATE_MODULE.parse_arms
validate_trajectory = GATE_MODULE.validate_trajectory
audit_checkout = GATE_MODULE.audit_checkout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_scoring_source(checkout: Path, gate: dict, scoring: dict) -> dict:
    source = audit_checkout(checkout)
    if gate.get("source_revision") != source["revision"]:
        raise ValueError("STATE-Bench source revision differs from the release gate")
    if gate.get("held_out_tasks") != source["test_split_count"]:
        raise ValueError("STATE-Bench test split differs from the release gate")
    if gate.get("runs_per_task") != source["official_runs_per_task"]:
        raise ValueError("STATE-Bench run contract differs from the release gate")
    if scoring.get("runs_per_task") != source["official_runs_per_task"]:
        raise ValueError("scoring contract differs from the qualified source")
    return source


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot compute a percentile of an empty sample")
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def interval(values: list[float]) -> list[float]:
    return [percentile(values, 0.025), percentile(values, 0.975)]


def load_records(
    arms: dict[str, Path], gate: dict, task_ids: list[str], runs: int
) -> dict[str, dict[str, list[dict]]]:
    expected_hashes = {
        (record["arm"], record["run"], record["task_id"]): record["sha256"]
        for record in gate["records"]
    }
    loaded: dict[str, dict[str, list[dict]]] = {}
    for arm, root in arms.items():
        if sha256(root / "ARM_MANIFEST.json") != gate["arm_manifests"][arm]:
            raise ValueError(f"{arm}: arm manifest differs from the release gate")
        artifact = gate["learning_artifacts"][arm]
        if artifact is not None:
            artifact_path = (root / artifact["relative_path"]).resolve()
            try:
                artifact_path.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"{arm}: learning artifact leaves its result directory") from exc
            if not artifact_path.is_file() or sha256(artifact_path) != artifact["sha256"]:
                raise ValueError(f"{arm}: learning artifact differs from the release gate")
        loaded[arm] = defaultdict(list)
        for run_index in range(1, runs + 1):
            for task_id in task_ids:
                path = root / f"run{run_index}" / f"{task_id}.json"
                expected = expected_hashes.get((arm, run_index, task_id))
                if expected is None or sha256(path) != expected:
                    raise ValueError(f"{arm}/run{run_index}/{task_id}: differs from release gate")
                loaded[arm][task_id].append(validate_trajectory(path, task_id))
    return loaded


def arm_summary(by_task: dict[str, list[dict]]) -> dict:
    rows = [row for task_rows in by_task.values() for row in task_rows]
    successes = [int(row["task_completion_pass"]) for row in rows]
    task_rates = {
        task_id: sum(int(row["task_completion_pass"]) for row in task_rows) / len(task_rows)
        for task_id, task_rows in by_task.items()
    }
    tool_calls = sum(float(row["tool_calls"]) for row in rows)
    tool_errors = sum(float(row["tool_errors"]) for row in rows)
    redundant_calls = sum(float(row["redundant_calls"]) for row in rows)
    costs = [row.get("cost_usd") for row in rows]
    cost_complete = all(isinstance(value, int | float) for value in costs)
    state_pass_task_fail = sum(
        int(row["state_requirements_met"] == 1 and row["task_requirements_met"] == 0)
        for row in rows
    )
    task_pass_state_fail = sum(
        int(row["task_requirements_met"] == 1 and row["state_requirements_met"] == 0)
        for row in rows
    )
    return {
        "task_completion_pass_at_1": sum(successes) / len(successes),
        "task_completion_pass_power_5": sum(rate == 1.0 for rate in task_rates.values())
        / len(task_rates),
        "mean_user_experience_score": sum(float(row["ux_score"]) for row in rows) / len(rows),
        "mean_cost_per_task": (
            sum(float(value) for value in costs if value is not None) / len(costs)
            if cost_complete
            else None
        ),
        "cost_accounting_complete": cost_complete,
        "state_pass_task_fail_count": state_pass_task_fail,
        "task_pass_state_fail_count": task_pass_state_fail,
        "tool_error_rate_per_tool_call": tool_errors / tool_calls if tool_calls else 0.0,
        "redundant_call_rate_per_tool_call": redundant_calls / tool_calls if tool_calls else 0.0,
        "task_success_rates": dict(sorted(task_rates.items())),
    }


def stratified_resample(task_types: dict[str, str], rng: random.Random) -> list[str]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for task_id, task_type in task_types.items():
        by_family[task_type].append(task_id)
    sample = []
    for task_type in sorted(by_family):
        task_ids = sorted(by_family[task_type])
        sample.extend(rng.choice(task_ids) for _ in task_ids)
    return sample


def mean_for_sample(task_rates: dict[str, float], sample: list[str]) -> float:
    return sum(task_rates[task_id] for task_id in sample) / len(sample)


def score(
    loaded: dict[str, dict[str, list[dict]]],
    task_types: dict[str, str],
    candidate_plan: dict,
    scoring: dict,
) -> dict:
    summaries = {arm: arm_summary(by_task) for arm, by_task in loaded.items()}
    baseline = scoring["baseline_arm"]
    candidates = scoring["candidate_arms"]
    predicted = scoring["predicted_choice"]
    means = {arm: summaries[arm]["task_completion_pass_at_1"] for arm in summaries}
    best_mean = max(means[arm] for arm in candidates)
    observed_best = sorted(arm for arm in candidates if means[arm] == best_mean)
    candidate_regret = best_mean - means[predicted]
    best_action_mean = max(means.values())
    observed_best_actions = sorted(arm for arm in means if means[arm] == best_action_mean)
    regret = best_action_mean - means[predicted]

    threshold = float(scoring["regression"]["material_threshold"])
    regressions = {}
    family_changes = {}
    for arm in candidates:
        differences = {
            task_id: summaries[arm]["task_success_rates"][task_id]
            - summaries[baseline]["task_success_rates"][task_id]
            for task_id in task_types
        }
        regressions[arm] = {
            "material_regression_count": sum(
                difference <= threshold + 1e-12 for difference in differences.values()
            ),
            "material_regression_task_ids": sorted(
                task_id
                for task_id, difference in differences.items()
                if difference <= threshold + 1e-12
            ),
            "task_success_changes": dict(sorted(differences.items())),
        }
        family_values: dict[str, list[float]] = defaultdict(list)
        for task_id, difference in differences.items():
            family_values[task_types[task_id]].append(difference)
        family_changes[arm] = {
            family: sum(values) / len(values) for family, values in sorted(family_values.items())
        }

    rng = random.Random(scoring["uncertainty"]["random_seed"])
    improvements = {arm: [] for arm in candidates}
    regrets = []
    candidate_regrets = []
    for _ in range(scoring["uncertainty"]["resamples"]):
        sample = stratified_resample(task_types, rng)
        sampled = {
            arm: mean_for_sample(summaries[arm]["task_success_rates"], sample) for arm in summaries
        }
        for arm in candidates:
            improvements[arm].append(sampled[arm] - sampled[baseline])
        candidate_regrets.append(max(sampled[arm] for arm in candidates) - sampled[predicted])
        regrets.append(max(sampled.values()) - sampled[predicted])

    pairwise = []
    for left, right in combinations(candidates, 2):
        pairwise.append(
            {
                "left": left,
                "right": right,
                "task_completion_difference": means[left] - means[right],
            }
        )

    return {
        "status": "HELD_OUT_OUTCOMES_RELEASED_AND_SCORED",
        "held_out_outcomes_opened": True,
        "predicted_choice": predicted,
        "observed_best_candidates": observed_best,
        "observed_best_actions_including_no_learning": observed_best_actions,
        "allocation_regret": regret,
        "allocation_regret_95_interval": interval(regrets),
        "candidate_only_allocation_regret": candidate_regret,
        "candidate_only_allocation_regret_95_interval": interval(candidate_regrets),
        "arm_summaries": summaries,
        "candidate_improvement_over_no_learning": {
            arm: {
                "point_estimate": means[arm] - means[baseline],
                "interval_95": interval(values),
            }
            for arm, values in improvements.items()
        },
        "pairwise_candidate_differences": pairwise,
        "task_regressions": regressions,
        "task_family_changes": family_changes,
        "trace_interpretation": scoring["trace_interpretation"],
        "candidate_membership_hashes": {
            arm: candidate_plan["candidates"][arm]["membership_sha256"] for arm in candidates
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--candidate-plan", type=Path, required=True)
    parser.add_argument("--scoring-contract", type=Path, required=True)
    parser.add_argument("--release-gate", type=Path, required=True)
    parser.add_argument("--arm", action="append", default=[], metavar="NAME=DIR")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    paths = {
        "candidate_plan": arguments.candidate_plan,
        "scoring_contract": arguments.scoring_contract,
        "release_gate": arguments.release_gate,
    }
    candidate_plan = json.loads(arguments.candidate_plan.read_text(encoding="utf-8"))
    scoring = json.loads(arguments.scoring_contract.read_text(encoding="utf-8"))
    gate = json.loads(arguments.release_gate.read_text(encoding="utf-8"))
    if gate.get("status") != "CANDIDATE_RESULTS_COMPLETE__NOT_SCORED":
        raise ValueError("release gate did not pass")
    if gate.get("held_out_outcomes_opened") is not True:
        raise ValueError("release gate does not record outcome opening")
    if gate.get("scientific_aggregates_computed") is not False:
        raise ValueError("release gate already contains scientific aggregates")
    if gate["inputs"]["candidate_plan_sha256"] != sha256(arguments.candidate_plan):
        raise ValueError("candidate plan differs from the release gate")
    if gate["inputs"]["scoring_contract_sha256"] != sha256(arguments.scoring_contract):
        raise ValueError("scoring contract differs from the release gate")

    arms = parse_arms(arguments.arm)
    if set(arms) != set(gate["arms"]):
        raise ValueError("result directories differ from the release gate")
    checkout = arguments.checkout.resolve()
    validate_scoring_source(checkout, gate, scoring)
    domain_root = checkout / "state_bench" / "domains" / "customer_support"
    split = json.loads((domain_root / "splits" / "train_test.json").read_text())["splits"]
    task_ids = list(split["test"])
    task_types = {
        task_id: json.loads((domain_root / "tasks" / f"{task_id}.json").read_text())["task_type"]
        for task_id in task_ids
    }
    loaded = load_records(arms, gate, task_ids, scoring["runs_per_task"])
    result = {
        "schema_version": 1,
        "study_id": scoring["study_id"],
        **score(loaded, task_types, candidate_plan, scoring),
        "learning_artifact_build_accounting": gate["learning_artifacts"],
        "inputs": {f"{name}_sha256": sha256(path) for name, path in paths.items()},
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "predicted_choice": result["predicted_choice"],
                "observed_best_candidates": result["observed_best_candidates"],
                "allocation_regret": result["allocation_regret"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
