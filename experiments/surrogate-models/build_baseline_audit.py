#!/usr/bin/env python3
"""Build the released-baseline audit for the surrogate-model program."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

SOURCES = {
    "materials": REPO
    / "experiments/ai-for-science/materials-science/retrospective-bridge"
    / "pooled_semantic_analysis.json",
    "finance": REPO
    / "experiments/finance/retrospective-post-training/results/expanded_summary_corrected.json",
    "mathematics": REPO
    / "experiments/mathematics/environment-utility/results/prospective/summary_scores.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def metric_view(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        key: metrics[key]
        for key in ("mean_normalized_regret", "pairwise_ordering", "top_choice_credit")
    }


def build_audit() -> dict[str, Any]:
    materials = load(SOURCES["materials"])
    finance = load(SOURCES["finance"])
    mathematics = load(SOURCES["mathematics"])

    materials_methods = materials["source_macro_metrics"]
    finance_methods = finance["evaluations"]["leave_one_source_out"]
    math_loso = mathematics["four_scale_leave_one_scale_out"]

    return {
        "artifact": "anarres_released_baseline_audit_v1",
        "evidence_tier": "released retrospective and prospective-result audit",
        "purpose": (
            "Fix the strongest released simple baselines that a central surrogate must beat; "
            "this artifact does not fit or score a new cross-domain model."
        ),
        "sources": {
            key: {"path": str(path.relative_to(REPO)), "sha256": sha256(path)}
            for key, path in SOURCES.items()
        },
        "studies": {
            "materials": {
                "split": "leave one publication source out",
                "support": materials["support"],
                "methods": {
                    "uninformed_tie": metric_view(materials_methods["uninformed_tie"]),
                    "released_native_rule": metric_view(materials_methods["semantic_mean"]),
                    "measurement_ridge": metric_view(materials_methods["ridge"]),
                },
                "strongest_released_method_by_regret": "released_native_rule",
                "ridge_minus_native_rule_regret": (
                    materials_methods["ridge"]["mean_normalized_regret"]
                    - materials_methods["semantic_mean"]["mean_normalized_regret"]
                ),
            },
            "finance": {
                "split": "leave one study source out",
                "support": finance["support"],
                "methods": {
                    "uninformed_tie": metric_view(finance_methods["uninformed"]["source_macro"]),
                    "released_native_rule": metric_view(
                        finance_methods["practical_rule"]["source_macro"]
                    ),
                    "metadata_ridge": metric_view(finance_methods["compact_ridge"]["source_macro"]),
                },
                "strongest_released_method_by_regret": "released_native_rule",
                "ridge_minus_native_rule_regret": (
                    finance_methods["compact_ridge"]["source_macro"]["mean_normalized_regret"]
                    - finance_methods["practical_rule"]["source_macro"]["mean_normalized_regret"]
                ),
            },
            "mathematics": {
                "split": "leave one model scale out",
                "support": {
                    "scales": 4,
                    "candidate_environments_per_scale": 4,
                    "matched_budgets_per_environment": 4,
                },
                "released_measurement_model": {
                    "curve_rmse_percentage_points": math_loso["curve_rmse"],
                    "pairwise_ordering": math_loso["pairwise_rank_accuracy_percent"] / 100.0,
                    "mean_allocation_regret_percentage_points": math_loso["mean_allocation_regret"],
                },
                "comparability_note": (
                    "Native percentage-point regret is retained because the released artifact "
                    "does not report the normalized study-macro regret used in the central audit."
                ),
            },
        },
        "findings": [
            (
                "The released native rule has lower study/source-macro regret than ridge "
                "in both materials and finance."
            ),
            (
                "The mathematics measurement model transfers across held-out scales, but "
                "its released regret remains in native percentage points."
            ),
            (
                "A central learned surrogate must be compared with domain-native rules and "
                "must not treat heterogeneous native feature names as interchangeable."
            ),
        ],
        "next_gate": (
            "Implement the frozen structured replay on compatible measurements and advance only "
            "if it improves complete-study holdouts over these released simple baselines."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=HERE / "BASELINE_AUDIT.json")
    args = parser.parse_args()

    rendered = json.dumps(build_audit(), indent=2, sort_keys=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            raise SystemExit(f"stale baseline audit: {args.output}")
        return
    args.output.write_text(rendered)


if __name__ == "__main__":
    main()
