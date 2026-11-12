#!/usr/bin/env python3
"""Produce a compact, claim-bounded summary of the molecular bridge."""

from __future__ import annotations

import argparse
import collections
import itertools
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


def load(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def summarize_pmo(payload: dict[str, Any]) -> dict[str, Any]:
    values: dict[tuple[str, str, int], list[float]] = collections.defaultdict(list)
    for row in payload["records"]:
        values[(row["task"], row["method"], row["oracle_budget"])].append(row["auc_top10"])
    means = {key: mean(items) for key, items in values.items()}
    tasks = sorted({key[0] for key in means})
    methods = sorted({key[1] for key in means})
    diagnostics = []
    for budget in (1000, 2500, 5000, 7500):
        exact = 0
        regrets = []
        concordant = 0.0
        total = 0
        for task in tasks:
            selected = max(methods, key=lambda method: means[(task, method, budget)])
            best = max(methods, key=lambda method: means[(task, method, 10000)])
            exact += selected == best
            regrets.append(means[(task, best, 10000)] - means[(task, selected, 10000)])
            for left, right in itertools.combinations(methods, 2):
                early = means[(task, left, budget)] - means[(task, right, budget)]
                final = means[(task, left, 10000)] - means[(task, right, 10000)]
                if early == 0 or final == 0:
                    concordant += 0.5
                elif early * final > 0:
                    concordant += 1.0
                total += 1
        diagnostics.append(
            {
                "pilot_budget_per_method": budget,
                "pilot_fraction_of_final_budget": budget / 10000,
                "exact_final_winner_tasks": exact,
                "tasks": len(tasks),
                "final_auc_top10_mean_regret": mean(regrets),
                "final_auc_top10_median_regret": median(regrets),
                "pairwise_final_rank_accuracy": concordant / total,
                "cost_note": (
                    "This diagnostic evaluates every method at the pilot budget and "
                    "does not charge that total pilot cost. It is descriptive, not "
                    "an allocation-policy result."
                ),
            }
        )

    fixed_regrets = []
    fixed_choices = []
    fixed_exact = 0
    for held_out in tasks:
        train_tasks = [task for task in tasks if task != held_out]
        selected = max(
            methods,
            key=lambda method: mean(means[(task, method, 10000)] for task in train_tasks),
        )
        best = max(methods, key=lambda method: means[(held_out, method, 10000)])
        fixed_choices.append(selected)
        fixed_exact += selected == best
        fixed_regrets.append(means[(held_out, best, 10000)] - means[(held_out, selected, 10000)])
    return {
        "support": payload["support"],
        "retrospective_pilot_diagnostics": diagnostics,
        "leave_one_task_out_fixed_method": {
            "selected_methods": dict(sorted(collections.Counter(fixed_choices).items())),
            "exact_final_winner_tasks": fixed_exact,
            "tasks": len(tasks),
            "final_auc_top10_mean_regret": mean(fixed_regrets),
            "final_auc_top10_median_regret": median(fixed_regrets),
        },
    }


def summarize_saturn(payload: dict[str, Any]) -> dict[str, Any]:
    architecture_best = {}
    for model in sorted({row["model"] for row in payload["architecture_records"]}):
        rows = [row for row in payload["architecture_records"] if row["model"] == model]
        best = max(rows, key=lambda row: row["yield_mean"])
        architecture_best[model] = {
            "augmentation_rounds": best["augmentation_rounds"],
            "yield_mean": best["yield_mean"],
            "yield_sd": best["yield_sd"],
            "internal_diversity_mean": best["internal_diversity_mean"],
        }
    target_winners = {
        target: max(methods, key=methods.get)
        for target, methods in payload["hit_ratio_method_means_by_target"].items()
    }
    return {
        "support": payload["support"],
        "best_published_yield_condition_by_architecture": architecture_best,
        "five_target_hit_ratio_winners": dict(sorted(target_winners.items())),
        "winner_counts": dict(sorted(collections.Counter(target_winners.values()).items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pmo", type=Path, required=True)
    parser.add_argument("--invirtuo", type=Path, required=True)
    parser.add_argument("--saturn", type=Path, required=True)
    parser.add_argument("--antoniuk", type=Path, required=True)
    parser.add_argument("--tsmiles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    pmo = load(args.pmo)
    invirtuo = load(args.invirtuo)
    saturn = load(args.saturn)
    antoniuk = load(args.antoniuk)
    tsmiles = load(args.tsmiles)
    output = {
        "schema_version": "anarres.molecular.retrospective_bridge_summary.v1",
        "claim_boundary": (
            "The bridge combines distinct public scientific objects without "
            "pooling their native outcomes. The controlled RxnFlow study remains "
            "the environment-selection test. Antoniuk et al. test closed-loop "
            "active learning, InVirtuoGen tests replay, Saturn tests components "
            "and methods, t-SMILES audits representation and augmentation, and "
            "PMO tests finite-budget optimizers."
        ),
        "source_objects": 5,
        "antoniuk_active_learning": {
            "support": antoniuk["support"],
            "matched_generation_records": [
                row for row in antoniuk["table_2_records"] if row["oracle_budget"] == 500
            ],
            "released_batch_summaries": antoniuk["released_batch_summaries"],
        },
        "tsmiles_jnk3": {
            "support": tsmiles["support"],
            "highest_active_novel_conditions": sorted(
                tsmiles["records"],
                key=lambda row: row["active_novel_fraction"],
                reverse=True,
            )[:3],
        },
        "invirtuogen_replay": {
            "support": invirtuo["support"],
            "matched_seed0_summary": invirtuo["matched_seed0_summary"],
        },
        "saturn": summarize_saturn(saturn),
        "pmo": summarize_pmo(pmo),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
