#!/usr/bin/env python3
"""Build the localized-regression evidence audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "REGRESSION_EVIDENCE_AUDIT.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }


def build_audit() -> dict[str, Any]:
    coding_path = (
        ROOT / "experiments/agentic/coding-environment-selection/data/task-regression-risk.json"
    )
    legal_path = ROOT / "experiments/legal/lab-learning-dynamics/data/regression-risk.json"
    finance_path = (
        ROOT
        / "experiments/finance/retrospective-post-training/results/regression_risk_summary.json"
    )
    materials_relative_path = (
        ROOT
        / "experiments/ai-for-science/materials-science/retrospective-bridge"
        / "relative_harm_analysis.json"
    )
    materials_fit_path = (
        ROOT
        / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
        / "TARGET_REGRESSION_FIT.json"
    )
    materials_score_path = (
        ROOT
        / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
        / "PROSPECTIVE_PREDICTION_SCORE.json"
    )
    robotics_path = (
        ROOT
        / "experiments/robotics/environment-selection/prospective-square-regression-v1/RESULTS.json"
    )

    coding = read_json(coding_path)
    legal = read_json(legal_path)
    finance = read_json(finance_path)
    materials_relative = read_json(materials_relative_path)
    materials_score = read_json(materials_score_path)
    robotics = read_json(robotics_path)

    sources = [
        {
            "source_id": "coding_task_regressions",
            "domain": "agentic_coding",
            "endpoint_class": "localized_absolute_regression",
            "prediction_unit": "task by candidate environment",
            "independent_test_unit": "repository within one training study",
            "chronology": "retrospective reconstruction",
            "support": coding["support"],
            "primary_metrics": coding["metrics"]["combined"],
            "result": "signal within one intervention",
            "shared_model_eligibility": "development_only",
            "reason": (
                "The model separates tasks within the released study, but transfer to a new "
                "trainer, model family, or training intervention is untested."
            ),
            "artifacts": [artifact(coding_path)],
        },
        {
            "source_id": "legal_lab_task_regressions",
            "domain": "legal",
            "endpoint_class": "localized_absolute_regression",
            "prediction_unit": "LAB task",
            "independent_test_unit": "practice area within one training intervention",
            "chronology": "retrospective reconstruction",
            "support": legal["support"],
            "primary_metrics": legal["metrics"]["combined"],
            "result": "signal within one intervention",
            "shared_model_eligibility": "development_only",
            "reason": (
                "The model separates held-out practice areas within one intervention, but no "
                "independent intervention tests calibration."
            ),
            "artifacts": [artifact(legal_path)],
        },
        {
            "source_id": "materials_relative_harm",
            "domain": "materials_science",
            "endpoint_class": "candidate_relative_underperformance",
            "prediction_unit": "candidate environment against a matched reference",
            "independent_test_unit": "complete published source",
            "chronology": "retrospective leave-source-out audit",
            "support": materials_relative["support"],
            "primary_metrics": materials_relative["primary"]["semantic_relative_score"][
                "source_macro"
            ],
            "result": "source-held-out relative-harm signal",
            "shared_model_eligibility": "utility_safety_comparator",
            "reason": (
                "This predicts candidate underperformance, not which individual material "
                "regresses from a common starting checkpoint."
            ),
            "artifacts": [artifact(materials_relative_path)],
        },
        {
            "source_id": "materials_target_regressions",
            "domain": "materials_science",
            "endpoint_class": "localized_absolute_regression",
            "prediction_unit": "target material by candidate environment",
            "independent_test_unit": "target material with candidate environments grouped",
            "chronology": "prospectively frozen predictions",
            "support": {
                "candidate_material_pairs": 200,
                "regression_prevalence": 0.895,
            },
            "primary_metrics": {
                "roc_auc": materials_score["target_regressions"]["roc_auc"],
                "average_precision": materials_score["target_regressions"]["average_precision"],
            },
            "result": "prospective prediction failed",
            "shared_model_eligibility": "negative_control_only",
            "reason": (
                "The frozen risk score did not discriminate material-level regressions; the "
                "high event prevalence also makes average precision uninformative by itself."
            ),
            "artifacts": [artifact(materials_fit_path), artifact(materials_score_path)],
        },
        {
            "source_id": "robotics_square_stratum_regressions",
            "domain": "robotics",
            "endpoint_class": "localized_change_ordering",
            "prediction_unit": "evaluation stratum by candidate environment",
            "independent_test_unit": "candidate training seed with strata nested",
            "chronology": "prospectively frozen risk ordering",
            "support": {
                "candidate_stratum_rows": len(robotics["candidate_by_stratum"]),
                "candidate_environments": len(robotics["arm_mean_success_rates"]),
            },
            "primary_metrics": robotics["regression"],
            "result": "prospective prediction reversed direction",
            "shared_model_eligibility": "negative_control_only",
            "reason": (
                "Higher frozen risk predicted larger improvements rather than regressions, so "
                "the current risk construction does not transfer."
            ),
            "artifacts": [artifact(robotics_path)],
        },
        {
            "source_id": "finance_candidate_regressions",
            "domain": "finance",
            "endpoint_class": "candidate_relative_underperformance",
            "prediction_unit": "candidate environment against a study-matched baseline",
            "independent_test_unit": "published source",
            "chronology": "retrospective secondary audit",
            "support": finance["support"],
            "primary_metrics": finance["rules"]["practical_rule"],
            "result": "source-macro relative-harm signal",
            "shared_model_eligibility": "utility_safety_comparator",
            "reason": (
                "The endpoint detects whether a whole candidate underperforms its baseline; it "
                "does not localize regressions to tasks, workflows, or states."
            ),
            "artifacts": [artifact(finance_path)],
        },
    ]

    return {
        "artifact": "anarres_regression_evidence_audit_v1",
        "status": "development audit; no shared localized-regression model is qualified",
        "question": (
            "Which released sources can support prediction of where a candidate training "
            "environment will cause regressions?"
        ),
        "endpoint_classes": {
            "localized_absolute_regression": (
                "a task or target becomes worse than the common starting policy"
            ),
            "localized_change_ordering": (
                "a pretraining risk score orders task or state changes after training"
            ),
            "candidate_relative_underperformance": (
                "a whole candidate performs worse than a study-matched alternative"
            ),
        },
        "sources": sources,
        "summary": {
            "released_sources": len(sources),
            "localized_sources": 4,
            "localized_sources_within_intervention_signal": 2,
            "localized_prospective_tests": 2,
            "localized_prospective_successes": 0,
            "relative_harm_sources": 2,
        },
        "decision": {
            "fit_shared_localized_model": False,
            "next": (
                "freeze a new independent intervention using one native localized endpoint, "
                "score the existing domain model and a measurement-only baseline, and retain "
                "the starting-policy option before testing shared representations"
            ),
            "why": [
                (
                    "the positive localized results are retrospective and nested within one "
                    "intervention"
                ),
                "both prospective localized tests failed",
                "relative candidate harm is useful but is not a localized regression label",
                "pooling rows would turn nested tasks, materials, or strata into false sample size",
            ],
        },
        "rules": [
            "preserve each native regression definition and independent unit",
            "report discrimination and calibration when the endpoint is probabilistic",
            "hold out complete interventions before claiming transfer",
            "keep candidate-level relative harm separate from localized regression",
            "retain failed prospective tests as negative controls",
        ],
    }


def render() -> str:
    return json.dumps(build_audit(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render()
    if args.check:
        if args.output.read_text() != text:
            raise SystemExit("stale regression-evidence audit")
        return
    args.output.write_text(text)


if __name__ == "__main__":
    main()
