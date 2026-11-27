#!/usr/bin/env python3
"""Build the domain-centered utility and regression inventory.

This is the second corpus view. It preserves the first frozen replay and adds
agentic coding without treating mathematics as headline supervision. Utility
records and nested regression evidence remain separate prediction tracks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_RECORDS = HERE / "CORPUS_RECORDS.jsonl"
DEFAULT_OUTPUT = HERE / "DOMAIN_SURROGATE_INVENTORY.json"
DEFAULT_RECORDS = HERE / "DOMAIN_SURROGATE_RECORDS.jsonl"
PRIORITY_DOMAINS = {"finance", "legal", "materials_science", "robotics"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": relative(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def slug(*parts: object) -> str:
    return ":".join(str(part).replace(":", "_") for part in parts)


def load_priority_records() -> list[dict[str, Any]]:
    records = [json.loads(line) for line in BASE_RECORDS.read_text().splitlines()]
    return [record for record in records if record["domain"] in PRIORITY_DOMAINS]


def primary_coding_panels(path: Path) -> list[dict[str, Any]]:
    panels = []
    for panel in read_json(path)["panels"]:
        measurements = {}
        candidates = {}
        for candidate in panel["candidates"]:
            readiness = float(candidate["readiness"])
            score = (
                float(candidate["reward_information"]) / float(candidate["cost"])
                if 0.10 <= readiness <= 0.85
                else -1.0
            )
            measurements[str(candidate["id"])] = score
            candidates[str(candidate["id"])] = {
                key: value for key, value in candidate.items() if key != "id"
            }
        source = str(panel["panel_id"]).split("_")[0]
        for endpoint, outcomes in panel["outcomes"].items():
            panels.append(
                {
                    "source_id": source,
                    "decision_id": panel["panel_id"],
                    "panel_id": f"{panel['panel_id']}__{endpoint}",
                    "outcome_name": endpoint,
                    "outcomes": {key: 100 * float(value) for key, value in outcomes.items()},
                    "measurements": measurements,
                    "candidate_inputs": candidates,
                    "chronology": panel["chronology"],
                }
            )
    return panels


def external_coding_panels(path: Path) -> list[dict[str, Any]]:
    panels = []
    for panel in read_json(path)["panels"]:
        candidates = {str(row["id"]): row for row in panel["candidates"]}
        panels.append(
            {
                "source_id": panel["source_id"],
                "decision_id": panel["panel_id"],
                "panel_id": panel["panel_id"],
                "outcome_name": panel["evaluation"],
                "outcomes": {key: float(row["score"]) for key, row in candidates.items()},
                "measurements": {
                    key: float(row["policy_aligned_progression"]) for key, row in candidates.items()
                },
                "candidate_inputs": {
                    key: {k: v for k, v in row.items() if k not in {"id", "score"}}
                    for key, row in candidates.items()
                },
                "chronology": "retrospective_source_separated_external_check",
            }
        )
    return panels


def added_coding_panels(path: Path) -> list[dict[str, Any]]:
    panels = []
    for panel in read_json(path)["panels"]:
        candidates = {str(row["id"]): row for row in panel["candidates"]}
        panels.append(
            {
                "source_id": panel["source_id"],
                "decision_id": panel.get("decision_id", panel["panel_id"]),
                "panel_id": panel["panel_id"],
                "outcome_name": panel["evaluation"],
                "outcomes": {key: float(row["score"]) for key, row in candidates.items()},
                "measurements": {
                    key: float(row["measurement_score"]) for key, row in candidates.items()
                },
                "candidate_inputs": {
                    key: {"measurement_score": float(row["measurement_score"])}
                    for key, row in candidates.items()
                },
                "chronology": "retrospective_public_evidence",
            }
        )
    return panels


def coding_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base = ROOT / "experiments/agentic/coding-environment-selection"
    paths = {
        "primary": base / "data/panels.json",
        "external": base / "data/external-forecast-panels.json",
        "additions": base / "data/bridge-additions.json",
    }
    panels = [
        *primary_coding_panels(paths["primary"]),
        *external_coding_panels(paths["external"]),
        *added_coding_panels(paths["additions"]),
    ]
    source_files: dict[str, set[Path]] = {}
    for panel in primary_coding_panels(paths["primary"]):
        source_files.setdefault(panel["source_id"], set()).add(paths["primary"])
    for panel in external_coding_panels(paths["external"]):
        source_files.setdefault(panel["source_id"], set()).add(paths["external"])
    for panel in added_coding_panels(paths["additions"]):
        source_files.setdefault(panel["source_id"], set()).add(paths["additions"])

    records = []
    for panel in panels:
        for candidate, outcome in panel["outcomes"].items():
            records.append(
                {
                    "record_id": slug("agentic_coding", panel["panel_id"], candidate),
                    "source_id": f"agentic_coding_{panel['source_id']}",
                    "domain": "agentic_coding",
                    "study_id": slug("agentic_coding", panel["source_id"], panel["decision_id"]),
                    "panel_id": panel["panel_id"],
                    "candidate_id": candidate,
                    "training_run_id": None,
                    "seed": None,
                    "evidence_level": "published_candidate_arm_aggregate",
                    "record_pointer": {"source_panel": panel["panel_id"]},
                    "prediction_time": {
                        **panel["candidate_inputs"][candidate],
                        "source_native_measurement_score": panel["measurements"][candidate],
                    },
                    "outcome": {
                        "name": panel["outcome_name"],
                        "value": outcome,
                        "higher_is_better": True,
                    },
                    "cost": {"status": "missing"},
                    "grouping": {
                        "lineage": slug(panel["decision_id"], candidate),
                        "decision_id": panel["decision_id"],
                        "nested_endpoint": panel["panel_id"],
                    },
                    "chronology": panel["chronology"],
                }
            )
    sources = [
        {
            "source_id": f"agentic_coding_{source}",
            "domain": "agentic_coding",
            "evidence_level": "published_candidate_arm_aggregate",
            "artifacts": [artifact(path) for path in sorted(files)],
        }
        for source, files in sorted(source_files.items())
    ]
    return records, sources


def roc_auc(labels: list[bool], scores: list[float]) -> float:
    positives = [score for label, score in zip(labels, scores, strict=True) if label]
    negatives = [score for label, score in zip(labels, scores, strict=True) if not label]
    if not positives or not negatives:
        raise ValueError("ROC AUC requires both outcome classes")
    credits = sum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return credits / (len(positives) * len(negatives))


def binary_metrics(labels: list[bool], scores: list[float]) -> dict[str, Any]:
    count = len(labels)
    top = max(1, round(0.2 * count))
    selected = sorted(range(count), key=lambda index: scores[index], reverse=True)[:top]
    positives = sum(labels)
    return {
        "examples": count,
        "positive_rate": round(positives / count, 12),
        "roc_auc": round(roc_auc(labels, scores), 12),
        "brier": round(
            sum((score - float(label)) ** 2 for label, score in zip(labels, scores, strict=True))
            / count,
            12,
        ),
        "top_20pct_recall": round(
            sum(labels[index] for index in selected) / positives,
            12,
        ),
    }


def regression_sources() -> list[dict[str, Any]]:
    legal_path = ROOT / "experiments/legal/lab-learning-dynamics/data/regression-risk.json"
    legal = read_json(legal_path)
    coding_path = (
        ROOT / "experiments/agentic/coding-environment-selection/data/task-regression-risk.json"
    )
    coding = read_json(coding_path)
    materials_base = (
        ROOT / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
    )
    materials_fit_path = materials_base / "TARGET_REGRESSION_FIT.json"
    materials_outcomes_path = materials_base / "PROSPECTIVE_OUTCOMES.json"
    materials_fit = read_json(materials_fit_path)
    materials_outcomes = read_json(materials_outcomes_path)
    predicted = {
        (row["candidate_id"], row["target_material_id"]): float(
            row["frequency_error_regression_probability"]
        )
        for row in materials_fit["prospective_predictions"]
    }
    observed = {
        (row["candidate_id"], row["target_material_id"]): bool(row["frequency_error_regression"])
        for row in materials_outcomes["target_regressions"]
    }
    if set(predicted) != set(observed):
        raise ValueError("materials prospective prediction and outcome keys differ")
    keys = sorted(predicted)
    materials_metrics = binary_metrics(
        [observed[key] for key in keys], [predicted[key] for key in keys]
    )

    robotics_path = (
        ROOT
        / "experiments/robotics/environment-selection/prospective-square-regression-v1/RESULTS.json"
    )
    robotics = read_json(robotics_path)
    return [
        {
            "domain": "legal",
            "source_id": "legal_lab_task_regressions",
            "artifacts": [artifact(legal_path)],
            "prediction_unit": "LAB task",
            "independent_holdout_unit": legal["support"]["independent_generalization_unit"],
            "interventions": legal["support"]["trained_interventions"],
            "examples": legal["support"]["tasks"],
            "status": "retrospective within one intervention",
            "metrics": legal["metrics"]["combined"],
            "boundary": legal["claim_boundary"],
        },
        {
            "domain": "agentic_coding",
            "source_id": "coding_task_regressions",
            "artifacts": [artifact(coding_path)],
            "prediction_unit": "held-out coding task by candidate environment",
            "independent_holdout_unit": "repository",
            "interventions": coding["support"]["candidate_environments"],
            "examples": coding["support"]["task_environment_outcomes"],
            "status": "retrospective within one training study",
            "metrics": coding["metrics"]["combined"],
            "boundary": coding["claim_boundary"],
        },
        {
            "domain": "materials_science",
            "source_id": "materials_target_regressions",
            "artifacts": [artifact(materials_fit_path), artifact(materials_outcomes_path)],
            "prediction_unit": "target material by candidate environment",
            "independent_holdout_unit": "target material; candidate environments remain grouped",
            "interventions": materials_outcomes["counts"]["environments"],
            "examples": len(keys),
            "status": "development fit with prospectively frozen target predictions",
            "metrics": materials_metrics,
            "boundary": materials_fit["prospective_boundary"],
        },
        {
            "domain": "robotics",
            "source_id": "robotics_square_stratum_regressions",
            "artifacts": [artifact(robotics_path)],
            "prediction_unit": "evaluation stratum by candidate environment",
            "independent_holdout_unit": "candidate training seed; strata remain nested",
            "interventions": len(robotics["arm_mean_success_rates"]),
            "examples": len(robotics["candidate_by_stratum"]),
            "status": "prospective risk ordering; not a calibrated event model",
            "metrics": {
                "spearman_risk_vs_success_change": robotics["regression"][
                    "spearman_risk_vs_success_change"
                ],
                "spearman_95_interval": robotics["regression"]["spearman_95_interval"],
                "high_minus_low_risk_success_change": robotics["regression"][
                    "high_minus_low_risk_success_change"
                ],
                "tail_contrast_95_interval": robotics["regression"]["tail_contrast_95_interval"],
            },
            "boundary": [
                "strata are nested evaluation summaries, not independent interventions",
                "the released result evaluates risk ordering rather than event calibration",
            ],
        },
    ]


def build_inventory() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base_records = load_priority_records()
    coding, coding_sources = coding_records()
    records = sorted([*base_records, *coding], key=lambda row: row["record_id"])
    ids = [row["record_id"] for row in records]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate utility record IDs")
    panels: dict[tuple[str, str], set[str]] = {}
    for row in records:
        panels.setdefault((row["source_id"], row["panel_id"]), set()).add(row["candidate_id"])
    if any(len(candidates) < 2 for candidates in panels.values()):
        raise ValueError("every utility panel must contain at least two candidates")
    regressions = regression_sources()
    utility_by_domain = Counter(row["domain"] for row in records)
    level_counts = Counter(row["evidence_level"] for row in records)
    decisions = {(row["domain"], row["study_id"]) for row in records}
    inventory = {
        "artifact": "anarres_domain_surrogate_inventory_v2",
        "status": "development corpus; no general or prospective surrogate claim",
        "objective": (
            "forecast target-conditional utility, localized regression risk, cost, and "
            "uncertainty before candidate training"
        ),
        "tracks": {
            "utility": {
                "independent_unit": "training intervention or marked published aggregate",
                "records": len(records),
                "panels": len(panels),
                "study_or_decision_groups": len(decisions),
                "records_by_domain": dict(sorted(utility_by_domain.items())),
                "records_by_evidence_level": dict(sorted(level_counts.items())),
            },
            "regression": {
                "sources": len(regressions),
                "domains": sorted(row["domain"] for row in regressions),
                "rule": (
                    "tasks, materials, and strata remain nested under their intervention; "
                    "they never increase the intervention sample size"
                ),
            },
        },
        "domain_status": {
            "legal": "utility panel and task-regression evidence",
            "robotics": "three utility panels and prospective stratum-risk evidence",
            "materials_science": "utility panels and prospective target-regression evidence",
            "finance": "retrospective utility panels; localized regression labels absent",
            "agentic_coding": "utility decisions and task-regression evidence",
            "mathematics": "retained only in the first replay as a conformance fixture",
        },
        "coding_sources": coding_sources,
        "regression_sources": regressions,
        "records_artifact": {
            "path": DEFAULT_RECORDS.name,
            "records": len(records),
        },
        "release_gate": {
            "next": (
                "qualify retrieval and model choices on development groups, then freeze a "
                "new complete-study replay before opening its outcomes"
            ),
            "prohibited": [
                "selecting a new model on the already scored six-study replay",
                "pooling native outcomes into one cross-domain scalar label",
                "treating tasks, targets, strata, endpoints, or seeds as new studies",
            ],
        },
    }
    return inventory, records


def render() -> tuple[str, str]:
    inventory, records = build_inventory()
    records_text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in records)
    inventory["records_artifact"]["sha256"] = hashlib.sha256(records_text.encode()).hexdigest()
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n", records_text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--records-output", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    inventory_text, records_text = render()
    if args.check:
        if (
            args.output.read_text() != inventory_text
            or args.records_output.read_text() != records_text
        ):
            raise SystemExit("stale domain-surrogate inventory")
        return
    args.output.write_text(inventory_text)
    args.records_output.write_text(records_text)


if __name__ == "__main__":
    main()
