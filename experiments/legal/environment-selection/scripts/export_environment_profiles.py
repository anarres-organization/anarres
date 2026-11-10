#!/usr/bin/env python3
"""Export real SylloGym pre-training measurements as Anarres profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from anarres.environments import (
    build_profile_input,
    coordinate,
    local_artifact,
    qualification_check,
    write_profile_input,
)

STUDY = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = STUDY / "data" / "measurement-release.json"
DEFAULT_MEASUREMENTS = STUDY / "data" / "pretraining-task-measurements.json"
DEFAULT_SELECTOR = STUDY / "data" / "selector-freeze.json"
DEFAULT_DECISION = STUDY / "data" / "frozen-decision.json"
DEFAULT_SOURCES = STUDY / "SOURCES.json"
CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/legal-policy-response-v1.md"
)
ADAPTER_ID = "legal.syllogym-policy-response"
ADAPTER_REVISION = "v1"
EXPECTED_FIELDS = {
    "readiness",
    "binary_entropy_nats",
    "eligible_fraction",
    "format_fraction",
    "mean_generated_tokens",
    "truncation_fraction",
}


class AdapterError(ValueError):
    """Raised when the released evidence cannot support exact profile export."""


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterError(f"expected an object in {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)


def validate_inputs(
    release: dict[str, Any],
    measurements: dict[str, Any],
    selector: dict[str, Any],
    decision: dict[str, Any],
    sources: dict[str, Any],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    """Fail closed unless the complete outcome-blind release is internally consistent."""

    if release.get("schema_version") != "anarres.legal-syllogym-measurement-release.v1":
        raise AdapterError("unsupported SylloGym measurement-release schema")
    if release.get("status") != "complete_outcome_blind_pretraining_measurement":
        raise AdapterError("SylloGym pre-training measurement is not complete")
    boundary = release.get("outcome_boundary", {})
    if boundary != {
        "candidate_training_outcomes_used": False,
        "target_evaluation_outcomes_used": False,
        "outcomes_artifact_is_not_an_adapter_input": True,
    }:
        raise AdapterError("outcome boundary is absent or not sealed")
    for name, expected in release.get("native_artifacts", {}).items():
        if name not in paths or sha256(paths[name]) != expected:
            raise AdapterError(f"native artifact digest mismatch: {name}")

    source_rows = {item["name"]: item for item in sources.get("sources", [])}
    syllogym = source_rows.get("SylloGym")
    model = source_rows.get("Qwen3-4B Unsloth 4-bit")
    if not syllogym or not model:
        raise AdapterError("source or starting-policy provenance is absent")
    if any(syllogym.get(key) != release["source"][key] for key in ("uri", "revision", "license")):
        raise AdapterError("SylloGym source pin differs from the release")
    subject = release["subject"]
    if model.get("uri") != f"https://huggingface.co/{subject['id']}":
        raise AdapterError("starting-policy repository differs from the release")
    if model.get("revision") != subject["revision"]:
        raise AdapterError("starting-policy revision differs from the release")
    if model.get("weight_sha256") != subject["weight_sha256"]:
        raise AdapterError("starting-policy weight digest differs from the release")

    if measurements.get("outcome_blind") is not True:
        raise AdapterError("pre-training measurements are not marked outcome-blind")
    tasks = measurements.get("tasks")
    contract = release["measurement_contract"]
    if not isinstance(tasks, list) or len(tasks) != contract["generators"]:
        raise AdapterError("pre-training measurements have incomplete generator support")
    names: set[str] = set()
    expected_attempts = contract["independent_attempts_per_generator"]
    for task in tasks:
        name = task.get("task_name")
        if not isinstance(name, str) or not name or name in names:
            raise AdapterError("task identity is absent or duplicated")
        names.add(name)
        if task.get("attempts") != expected_attempts:
            raise AdapterError(f"{name} has an incomplete attempt count")
        if task.get("unique_source_attempt_ids") != expected_attempts:
            raise AdapterError(f"{name} does not preserve independent attempt identities")
        if task.get("reliability_gate") is not True:
            raise AdapterError(f"{name} fails the frozen reliability gate")
        for field in EXPECTED_FIELDS:
            value = task.get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise AdapterError(f"{name} has an invalid {field}")
        for field in ("readiness", "eligible_fraction", "format_fraction", "truncation_fraction"):
            if not 0.0 <= float(task[field]) <= 1.0:
                raise AdapterError(f"{name} has an out-of-range {field}")
        if task["binary_entropy_nats"] < 0 or task["mean_generated_tokens"] <= 0:
            raise AdapterError(f"{name} has invalid entropy or token cost")

    if selector.get("artifact") != "SYLLOGYM_STAGE_A_SELECTOR_FREEZE_V1":
        raise AdapterError("selector-freeze identity is absent")
    if selector.get("status") != "FROZEN_BEFORE_CANDIDATE_TRAINING":
        raise AdapterError("selector was not frozen before candidate training")
    if selector.get("candidate_training_outcomes_read") is not False:
        raise AdapterError("selector freeze read candidate-training outcomes")
    gates = selector.get("gates", {})
    required_gates = ("complete_measurement", "all_tasks_reliable", "freeze_ready")
    if not all(gates.get(key) is True for key in required_gates):
        raise AdapterError("selector qualification gates do not pass")
    selector_hash = decision.get("immutable_input_sha256", {}).get("selector_freeze")
    if selector_hash != sha256(paths["selector-freeze.json"]):
        raise AdapterError("prospective decision does not bind the selector freeze")
    chronology = decision.get("chronology", {})
    if chronology.get("candidate_outcomes_read_before_selector_freeze") is not False:
        raise AdapterError("prospective decision chronology is not outcome-blind")

    candidate_ids = release.get("candidate_ids")
    if candidate_ids != [
        "published_depth_weighted_control",
        "uniform_14_task_control",
        "frozen_policy_response_allocation",
    ]:
        raise AdapterError("candidate identities changed")
    weights = {
        "published_depth_weighted_control": selector["comparators"][
            "published_depth_weighted_control"
        ],
        "uniform_14_task_control": selector["comparators"]["uniform_14_task_control"],
        "frozen_policy_response_allocation": selector["weights"],
    }
    for candidate_id, candidate_weights in weights.items():
        if set(candidate_weights) != names:
            raise AdapterError(f"{candidate_id} does not cover the measured generators")
        invalid_weight = any(
            not isinstance(value, (int, float)) or value <= 0
            for value in candidate_weights.values()
        )
        if invalid_weight:
            raise AdapterError(f"{candidate_id} has an invalid mixture weight")
        if not close(sum(candidate_weights.values()), 1.0):
            raise AdapterError(f"{candidate_id} weights do not sum to one")
    frozen_weights = decision["candidate_arms"]["frozen_policy_response_allocation"]["weights"]
    published_weights = decision["candidate_arms"]["published_depth_weighted_control"]["weights"]
    for name, value in weights["frozen_policy_response_allocation"].items():
        if not math.isclose(value, frozen_weights[name], rel_tol=0.0, abs_tol=1e-12):
            raise AdapterError("frozen policy-response weights differ from the decision record")
    for name, value in weights["published_depth_weighted_control"].items():
        if not math.isclose(value, published_weights[name], rel_tol=0.0, abs_tol=1e-12):
            raise AdapterError("published-control weights differ from the decision record")
    return tasks


def weighted_mean(tasks: dict[str, dict[str, Any]], weights: dict[str, float], field: str) -> float:
    return sum(weights[name] * float(tasks[name][field]) for name in weights)


def candidate_weights(selector: dict[str, Any]) -> dict[str, dict[str, float]]:
    return {
        "published_depth_weighted_control": selector["comparators"][
            "published_depth_weighted_control"
        ],
        "uniform_14_task_control": selector["comparators"]["uniform_14_task_control"],
        "frozen_policy_response_allocation": selector["weights"],
    }


def export_profiles(
    *,
    release_path: Path,
    measurements_path: Path,
    selector_path: Path,
    decision_path: Path,
    sources_path: Path,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Export one profile for each prospectively compared SylloGym mixture."""

    release = read_object(release_path)
    measurements = read_object(measurements_path)
    selector = read_object(selector_path)
    decision = read_object(decision_path)
    sources = read_object(sources_path)
    paths = {
        "measurement-release.json": release_path,
        "pretraining-task-measurements.json": measurements_path,
        "selector-freeze.json": selector_path,
        "frozen-decision.json": decision_path,
        "SOURCES.json": sources_path,
    }
    task_rows = validate_inputs(release, measurements, selector, decision, sources, paths)
    tasks = {row["task_name"]: row for row in task_rows}
    weights_by_candidate = candidate_weights(selector)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [output_dir / f"{name}.profile-input.json" for name in release["candidate_ids"]]
    if not force:
        existing = [path for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(existing[0])

    subject = release["subject"]
    contract = release["measurement_contract"]
    profiles = []
    total_attempts = contract["generators"] * contract["independent_attempts_per_generator"]
    definitions = {
        "readiness_fraction": ("target_affinity", "fraction", "contextual"),
        "eligible_response_fraction": ("signal", "fraction", "contextual"),
        "binary_reward_entropy_nats": ("signal", "nats", "contextual"),
        "mean_token_cost": ("cost", "generated_tokens_per_response", "lower"),
        "truncation_rate": ("reliability", "fraction", "lower"),
        "format_valid_fraction": ("reliability", "fraction", "higher"),
    }
    fields = {
        "readiness_fraction": "readiness",
        "eligible_response_fraction": "eligible_fraction",
        "binary_reward_entropy_nats": "binary_entropy_nats",
        "mean_token_cost": "mean_generated_tokens",
        "truncation_rate": "truncation_fraction",
        "format_valid_fraction": "format_fraction",
    }
    for candidate_id in release["candidate_ids"]:
        weights = weights_by_candidate[candidate_id]
        effective_coverage = 1.0 / (len(weights) * sum(value * value for value in weights.values()))
        coordinates = []
        for name, field in fields.items():
            role, unit, direction = definitions[name]
            coordinates.append(
                coordinate(
                    name=name,
                    definition_uri=f"{CONVENTION_URI}#{name.replace('_', '-')}",
                    definition_revision="v1-development",
                    role=role,
                    value=weighted_mean(tasks, weights, field),
                    unit=unit,
                    direction=direction,
                    estimator=f"candidate-weighted mean of per-generator {field}",
                    sample_count=total_attempts,
                )
            )
        coordinates.extend(
            [
                coordinate(
                    name="effective_task_coverage",
                    definition_uri=f"{CONVENTION_URI}#effective-task-coverage",
                    definition_revision="v1-development",
                    role="coverage",
                    value=effective_coverage,
                    unit="fraction",
                    direction="contextual",
                    estimator="normalized inverse Simpson effective count over mixture weights",
                    sample_count=len(weights),
                ),
                coordinate(
                    name="missingness_rate",
                    definition_uri=f"{CONVENTION_URI}#missingness-rate",
                    definition_revision="v1-development",
                    role="reliability",
                    value=0.0,
                    unit="fraction",
                    direction="lower",
                    estimator="missing expected component-policy measurements",
                    sample_count=total_attempts,
                ),
            ]
        )
        profile = build_profile_input(
            environment_id=f"syllogym-{candidate_id}",
            domain="legal-procedural-reasoning",
            subject={
                "kind": subject["kind"],
                "id": subject["id"],
                "revision": f"{subject['revision']}|weights:{subject['weight_sha256']}",
            },
            producer={"kind": "domain-adapter", "id": ADAPTER_ID, "revision": ADAPTER_REVISION},
            source=release["source"],
            measurement_contract={
                "kind": contract["kind"],
                "id": contract["id"],
                "revision": contract["revision"],
                "repetitions": contract["independent_attempts_per_generator"],
                "cost_unit": contract["cost_unit"],
            },
            qualification_checks=[
                qualification_check(
                    check_id="source-and-policy-pinned",
                    category="source",
                    status="pass",
                    severity="error",
                    summary="The SylloGym source and starting-policy bytes match the release pins.",
                ),
                qualification_check(
                    check_id="outcome-blind-measurement",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary=(
                        "The component measurements and mixture rule were frozen before "
                        "training outcomes."
                    ),
                ),
                qualification_check(
                    check_id="complete-independent-attempts",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary="All 14 generators contain 256 distinct pre-training attempts.",
                ),
                qualification_check(
                    check_id="component-reliability",
                    category="measurement",
                    status="pass",
                    severity="error",
                    summary=(
                        "Every component generator passes the frozen format, truncation, "
                        "and eligibility gate."
                    ),
                ),
            ],
            coordinates=coordinates,
            artifacts=[
                local_artifact(
                    role="measurement-release",
                    path=release_path,
                    uri="repo://experiments/legal/environment-selection/data/measurement-release.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                ),
                local_artifact(
                    role="native-measurements",
                    path=measurements_path,
                    uri="repo://experiments/legal/environment-selection/data/pretraining-task-measurements.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                    producing_run=release["release_id"],
                ),
                local_artifact(
                    role="decision-record",
                    path=decision_path,
                    uri="repo://experiments/legal/environment-selection/data/frozen-decision.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                ),
                local_artifact(
                    role="selector-freeze",
                    path=selector_path,
                    uri="repo://experiments/legal/environment-selection/data/selector-freeze.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                ),
            ],
            attributes={
                "candidate_id": candidate_id,
                "generator_count": len(weights),
                "component_attempts": total_attempts,
                "outcome_blind": True,
            },
        )
        profiles.append(profile)
    for output, profile in zip(outputs, profiles, strict=True):
        write_profile_input(output, profile, force=force)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument("--selector", type=Path, default=DEFAULT_SELECTOR)
    parser.add_argument("--decision", type=Path, default=DEFAULT_DECISION)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = export_profiles(
        release_path=args.release,
        measurements_path=args.measurements,
        selector_path=args.selector,
        decision_path=args.decision,
        sources_path=args.sources,
        output_dir=args.output_dir,
        force=args.force,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
