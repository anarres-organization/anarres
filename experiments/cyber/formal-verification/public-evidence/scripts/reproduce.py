#!/usr/bin/env python3
"""Recompute the compact formal-verification public-evidence summary."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "results" / "summary.json"


def canonical_json(value: dict[str, object]) -> str:
    """Serialize one released artifact in its byte-stable form."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def load(name: str) -> dict[str, object]:
    """Load one compact source-linked record."""
    return json.loads((ROOT / "data" / name).read_text())


def rounded(value: float) -> float:
    """Round derived values for a stable public artifact."""
    return round(value, 6)


def verusyn_score(data: dict[str, object]) -> dict[str, object]:
    """Score the target-matched data-environment rule."""
    top = 0
    pairwise = 0
    regrets = []
    for panel in data["panels"]:
        outcomes = panel["outcomes_percent"]
        selected = data["practical_rule"][panel["target"]]
        selected_value = outcomes[selected]
        best = max(outcomes.values())
        top += selected_value == best
        pairwise += sum(
            selected_value >= value
            for candidate, value in outcomes.items()
            if candidate != selected
        )
        regrets.append(best - selected_value)
    return {
        "top_choice_correct": top,
        "top_choice_total": len(data["panels"]),
        "pairwise_correct": pairwise,
        "pairwise_total": 2 * len(data["panels"]),
        "mean_allocation_regret_pp": rounded(statistics.mean(regrets)),
        "maximum_allocation_regret_pp": rounded(max(regrets)),
    }


def reform_score(data: dict[str, object]) -> dict[str, object]:
    """Test whether raw verifier success selects semantic specification quality."""
    raw_correct = 0
    semantic_correct = 0
    regrets = []
    for panel in data["panels"]:
        arms = panel["arms"]
        raw_selected = max(arms, key=lambda arm: arms[arm]["verification"])
        observed = max(arms, key=lambda arm: arms[arm]["spec_superiority"])
        raw_correct += raw_selected == observed
        semantic_correct += observed == "subset_reward"
        regrets.append(arms[observed]["spec_superiority"] - arms[raw_selected]["spec_superiority"])
    return {
        "raw_verifier_top_choice_correct": raw_correct,
        "top_choice_total": len(data["panels"]),
        "raw_verifier_mean_semantic_regret_pp": rounded(statistics.mean(regrets)),
        "semantic_control_top_choice_correct": semantic_correct,
    }


def formal_disco_score(data: dict[str, object]) -> dict[str, object]:
    """Score the source-defined target-coverage preference."""
    top = 0
    regrets = []
    for panel in data["panels"]:
        outcomes = panel["outcomes_percent"]
        selected = "formal_disco"
        best = max(outcomes.values())
        top += outcomes[selected] == best
        regrets.append(best - outcomes[selected])
    specialized = data["generation_comparison"]["specialized_workers"]
    monolithic = data["generation_comparison"]["monolithic_agent"]
    return {
        "top_choice_correct": top,
        "top_choice_total": len(data["panels"]),
        "mean_allocation_regret_pp": rounded(statistics.mean(regrets)),
        "verified_yield_advantage_pp": rounded(
            specialized["verified_programs_per_llm_call_percent"]
            - monolithic["verified_programs_per_llm_call_percent"]
        ),
    }


def vericoding_score(data: dict[str, object]) -> dict[str, object]:
    """Summarize cross-policy support without relabeling it as repeated coverage."""
    support = data["tasks_with_at_least_eight_model_outcomes"]
    partition = (
        support["all_reported_models_fail"]
        + support["all_reported_models_succeed"]
        + support["mixed_success_across_models"]
    )
    if partition != support["total"]:
        raise ValueError("Vericoding task-support partition is inconsistent")
    return {
        "eligible_tasks": support["total"],
        "mixed_success_tasks": support["mixed_success_across_models"],
        "mixed_success_fraction": rounded(
            support["mixed_success_across_models"] / support["total"]
        ),
    }


def policy_support_score(data: dict[str, object]) -> dict[str, object]:
    """Preserve contract-specific policy leaders without pooling scores."""
    leanlean = data["sources"]["leanlean"]
    leanlean_policies = leanlean["reported_policies"]
    vero = data["sources"]["vero"]
    vero_policies = vero["reported_policies"]
    forall = data["sources"]["forall_verisoftbench"]

    compression_leader = max(leanlean_policies, key=lambda row: row["mean_compression_percent"])
    cost_leader = min(leanlean_policies, key=lambda row: row["mean_cost_usd"])
    vero_code_leader = max(vero_policies, key=lambda row: row["code_and_proof_full_solves"])
    vero_proof_leader = max(vero_policies, key=lambda row: row["proof_only_full_solves"])

    return {
        "leanlean_policies": len(leanlean_policies),
        "leanlean_repositories": leanlean_policies[0]["repositories"],
        "leanlean_compression_leader": compression_leader["policy"],
        "leanlean_cost_leader": cost_leader["policy"],
        "vero_policies": len(vero_policies),
        "vero_repositories": vero_policies[0]["repositories"],
        "vero_code_and_proof_leader": vero_code_leader["policy"],
        "vero_proof_only_leader": vero_proof_leader["policy"],
        "forall_configurations": forall["configurations"],
        "forall_subset_tasks": forall["subset_tasks"],
        "uniform_policy_leader_across_contracts": False,
    }


def compute() -> dict[str, object]:
    """Compute the released cross-source summary."""
    anthropic = load("anthropic-oss-fuzz.json")
    return {
        "artifact": "formal_verification_public_evidence_summary_v1",
        "anthropic_production_target": {
            "proved_entry_points": anthropic["production_result"]["proved_entry_points"],
            "open_source_libraries": anthropic["production_result"]["open_source_libraries"],
            "public_release_entry_points": anthropic["public_proof_release"]["proved_entry_points"],
            "public_release_libraries": anthropic["public_proof_release"]["open_source_libraries"],
            "small_tasks": anthropic["finite_budget_panel"]["tasks"],
            "attempts_per_task_model": anthropic["finite_budget_panel"]["attempts_per_task_model"],
            "tokens_per_attempt": anthropic["finite_budget_panel"]["tokens_per_attempt"],
            "shared_workspace_token_reduction_percent": anthropic["reuse_result"][
                "shared_workspace_token_reduction_percent"
            ],
        },
        "formal_disco": formal_disco_score(load("formal-disco.json")),
        "policy_support": policy_support_score(load("policy-support.json")),
        "reform": reform_score(load("reform.json")),
        "vericoding": vericoding_score(load("vericoding.json")),
        "verusyn": verusyn_score(load("verusyn.json")),
    }


def main() -> None:
    """Print the recomputed summary and verify the committed result."""
    actual = compute()
    serialized = canonical_json(actual)
    if serialized != EXPECTED.read_text():
        raise SystemExit("recomputed evidence summary does not byte-match results/summary.json")
    print(serialized, end="")


if __name__ == "__main__":
    main()
