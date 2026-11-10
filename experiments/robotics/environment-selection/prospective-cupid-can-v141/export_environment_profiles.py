#!/usr/bin/env python3
"""Export the sealed Can v1.4.1 candidate measurements as CLI profiles."""

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

ROOT = Path(__file__).resolve().parents[4]
STUDY = ROOT / "experiments/robotics/environment-selection/prospective-cupid-can-v141"
DEFAULT_MEASUREMENTS = STUDY / "PROFILE_MEASUREMENTS.json"
DEFAULT_PROTOCOL = STUDY / "PROTOCOL.json"
DEFAULT_SOURCES = STUDY / "SOURCES.json"
DEFAULT_QUALIFICATION = STUDY / "QUALIFICATION.json"
CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/robotics-cupid-candidate-measurement-v1.md"
)
ADAPTER_ID = "robotics.cupid-can-v141-candidate-measurement"
ADAPTER_REVISION = "v2"
EXPECTED_SOURCE_DIGEST = "b6ceaed84c0335613a5001c900493b226481c132c792ec2cbdb99cb12c62baf0"


class AdapterError(ValueError):
    """Raised when native records cannot support an exact profile export."""


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


def dataset_source(sources: dict[str, Any]) -> dict[str, Any]:
    matches = [
        item
        for item in sources.get("sources", [])
        if item.get("name") == "RoboMimic Can multi-human low-dimensional dataset"
    ]
    if len(matches) != 1:
        raise AdapterError("SOURCES.json must contain exactly one Can dataset record")
    return matches[0]


def validate_inputs(
    measurements: dict[str, Any],
    protocol: dict[str, Any],
    sources: dict[str, Any],
    qualification: dict[str, Any],
    protocol_path: Path,
    qualification_path: Path,
) -> dict[str, Any]:
    if measurements.get("schema_version") != "anarres.robotics-cupid-candidate-measurements.v2":
        raise AdapterError("unsupported robotics measurement schema")
    if measurements.get("outcomes_read") is not False:
        raise AdapterError("candidate outcomes were opened before profile export")
    if (
        measurements.get("status")
        != "PRE_OUTCOME_MEASUREMENTS_COMPLETE__CANDIDATE_OUTCOMES_UNOPENED"
    ):
        raise AdapterError("pre-outcome candidate measurement is incomplete")
    study_id = measurements.get("study_id")
    if protocol.get("study_id") != study_id or qualification.get("study_id") != study_id:
        raise AdapterError("study identity differs across native records")
    native = measurements.get("native_inputs", {})
    if native.get("protocol_sha256") != sha256(protocol_path):
        raise AdapterError("measurement does not match the checked-in protocol")
    if native.get("qualification_sha256") != sha256(qualification_path):
        raise AdapterError("measurement does not match the checked-in qualification record")
    source = dataset_source(sources)
    if source.get("sha256") != EXPECTED_SOURCE_DIGEST:
        raise AdapterError("Can source digest is missing or differs from the frozen study")
    if measurements.get("source_dataset_sha256") != source["sha256"]:
        raise AdapterError("measurement and source dataset revisions differ")
    if not source.get("url") or not source.get("revision") or not source.get("license"):
        raise AdapterError("Can source lacks URI, revision, or license")
    subject = measurements.get("subject", {})
    checkpoints = subject.get("checkpoint_sha256", [])
    if len(checkpoints) != 3 or any(len(item) != 64 for item in checkpoints):
        raise AdapterError("measurement lacks three scoring-checkpoint identities")
    candidates = measurements.get("candidates", {})
    protocol_candidates = {
        item["id"]: item for item in protocol.get("candidates", []) if isinstance(item, dict)
    }
    expected_candidates = set(protocol_candidates)
    if set(candidates) != expected_candidates:
        raise AdapterError("measurement candidate set differs from the frozen protocol")
    measurement = measurements.get("measurement", {})
    expected_scores = measurement.get("expected_score_values")
    observed_scores = measurement.get("observed_score_values")
    missingness = measurement.get("score_missingness_rate")
    if expected_scores != 900 or observed_scores != expected_scores or missingness != 0.0:
        raise AdapterError("candidate measurement does not preserve complete score exposure")
    support = measurement.get("checkpoint_outcome_support")
    if not isinstance(support, list) or len(support) != 3:
        raise AdapterError("measurement lacks three checkpoint outcome-support records")
    for checkpoint in support:
        episodes = checkpoint.get("episodes")
        successes = checkpoint.get("successes")
        failures = checkpoint.get("failures")
        if episodes != 100 or successes + failures != episodes or min(successes, failures) <= 0:
            raise AdapterError("checkpoint outcome support is incomplete or degenerate")
    for candidate_id, candidate in candidates.items():
        if candidate.get("count", 0) <= 0 or len(candidate.get("membership_sha256", "")) != 64:
            raise AdapterError(f"invalid candidate identity: {candidate_id}")
        values = candidate.get("coordinates", {})
        if set(values) != {
            "mean_cupid_rank_percentile",
            "operator_tier_effective_coverage",
            "mean_demonstration_action_steps",
            "measurement_rank_reliability",
        }:
            raise AdapterError(f"candidate lacks a complete measurement vector: {candidate_id}")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values.values()
        ):
            raise AdapterError(f"candidate contains a nonfinite coordinate: {candidate_id}")
    return source


def export_profiles(
    *,
    measurements_path: Path,
    protocol_path: Path,
    sources_path: Path,
    qualification_path: Path,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    measurements = read_object(measurements_path)
    protocol = read_object(protocol_path)
    sources = read_object(sources_path)
    qualification = read_object(qualification_path)
    source = validate_inputs(
        measurements,
        protocol,
        sources,
        qualification,
        protocol_path,
        qualification_path,
    )

    outputs = [
        output_dir / f"can-v141-{candidate_id}.profile-input.json"
        for candidate_id in sorted(measurements["candidates"])
    ]
    if not force:
        existing = [path for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    output_dir.mkdir(parents=True, exist_ok=True)

    reliability_passed = measurements["measurement"]["reliability_gate_passed"]
    qualification_passed = qualification.get("passed") is True
    protocol_candidates = {item["id"]: item for item in protocol["candidates"]}
    support = measurements["measurement"]["checkpoint_outcome_support"]
    support_episodes = sum(item["episodes"] for item in support)
    support_failures = sum(item["failures"] for item in support)
    profiles = []
    for candidate_id in sorted(measurements["candidates"]):
        candidate = measurements["candidates"][candidate_id]
        construction = protocol_candidates[candidate_id]["construction"]
        values = candidate["coordinates"]
        profiles.append(
            build_profile_input(
                environment_id=f"robomimic-can-v141-{candidate_id}",
                domain="robotics",
                subject={
                    "kind": measurements["subject"]["kind"],
                    "id": measurements["subject"]["id"],
                    "revision": measurements["subject"]["revision"],
                },
                producer={
                    "kind": "domain-adapter",
                    "id": ADAPTER_ID,
                    "revision": ADAPTER_REVISION,
                },
                source={
                    "uri": source["url"],
                    "revision": f"sha256:{source['sha256']}",
                    "license": source["license"],
                },
                measurement_contract={
                    "kind": "multi-checkpoint-performance-influence-measurement",
                    "id": "robotics.cupid-can-v141-candidate-measurement.v1",
                    "revision": "v1",
                    "repetitions": measurements["measurement"]["scoring_checkpoints"],
                    "cost_unit": "optimizer_steps",
                },
                qualification_checks=[
                    qualification_check(
                        check_id="closed-loop-outcome-support",
                        category="measurement",
                        status="pass" if qualification_passed else "fail",
                        severity="error",
                        summary=(
                            "The scoring policy produced both successful and failed episodes."
                            if qualification_passed
                            else (
                                "The scoring policy did not establish the required outcome support."
                            )
                        ),
                    ),
                    qualification_check(
                        check_id="measurement-reliability",
                        category="measurement",
                        status="pass" if reliability_passed else "fail",
                        severity="error",
                        summary=(
                            "The three checkpoint rankings passed the frozen reliability gate."
                            if reliability_passed
                            else "The checkpoint rankings failed the frozen reliability gate."
                        ),
                    ),
                    qualification_check(
                        check_id="candidate-outcomes-sealed",
                        category="robotics.chronology",
                        status="pass",
                        severity="error",
                        summary=(
                            "Candidate identities and measurements were released before "
                            "outcomes opened."
                        ),
                    ),
                ],
                coordinates=[
                    coordinate(
                        name="mean_cupid_rank_percentile",
                        definition_uri=CONVENTION_URI,
                        definition_revision="v1",
                        role="target_affinity",
                        value=float(values["mean_cupid_rank_percentile"]),
                        unit="rank_percentile",
                        direction="contextual",
                        estimator="candidate mean of three-checkpoint merged ordinal CUPID ranks",
                        sample_count=int(candidate["count"]),
                    ),
                    coordinate(
                        name="operator_tier_effective_coverage",
                        definition_uri=CONVENTION_URI,
                        definition_revision="v1",
                        role="coverage",
                        value=float(values["operator_tier_effective_coverage"]),
                        unit="fraction",
                        direction="higher",
                        estimator="normalized effective sample size across three operator tiers",
                        sample_count=int(candidate["count"]),
                    ),
                    coordinate(
                        name="mean_demonstration_action_steps",
                        definition_uri=CONVENTION_URI,
                        definition_revision="v1",
                        role="cost",
                        value=float(values["mean_demonstration_action_steps"]),
                        unit="action_steps_per_demonstration",
                        direction="lower",
                        estimator="arithmetic mean over selected demonstration lengths",
                        sample_count=int(candidate["count"]),
                    ),
                    coordinate(
                        name="measurement_rank_reliability",
                        definition_uri=CONVENTION_URI,
                        definition_revision="v1",
                        role="reliability",
                        value=float(values["measurement_rank_reliability"]),
                        unit="spearman_correlation",
                        direction="higher",
                        estimator=(
                            "mean pairwise Spearman correlation across three checkpoint rankings"
                        ),
                        sample_count=3,
                    ),
                ],
                artifacts=[
                    local_artifact(
                        role="native-measurements",
                        path=measurements_path,
                        uri=(
                            "repo://experiments/robotics/environment-selection/"
                            "prospective-cupid-can-v141/PROFILE_MEASUREMENTS.json"
                        ),
                        media_type="application/json",
                        license_id="Apache-2.0",
                        producing_run=measurements["study_id"],
                    ),
                    local_artifact(
                        role="measurement-contract",
                        path=protocol_path,
                        uri=(
                            "repo://experiments/robotics/environment-selection/"
                            "prospective-cupid-can-v141/PROTOCOL.json"
                        ),
                        media_type="application/json",
                        license_id="Apache-2.0",
                    ),
                    local_artifact(
                        role="qualification",
                        path=qualification_path,
                        uri=(
                            "repo://experiments/robotics/environment-selection/"
                            "prospective-cupid-can-v141/QUALIFICATION.json"
                        ),
                        media_type="application/json",
                        license_id="Apache-2.0",
                    ),
                ],
                attributes={
                    "candidate_id": candidate_id,
                    "candidate_count": int(candidate["count"]),
                    "candidate_construction": construction,
                    "tier_balance_constraint_applied": candidate_id == "cupid_tier_balanced_50",
                    "better_tier_count": int(candidate["tier_counts"]["better"]),
                    "okay_tier_count": int(candidate["tier_counts"]["okay"]),
                    "worse_tier_count": int(candidate["tier_counts"]["worse"]),
                    "membership_sha256": candidate["membership_sha256"],
                    "selected_fraction": candidate["count"]
                    / measurements["measurement"]["demonstrations"],
                    "selected_fraction_unit": "fraction_of_demonstration_pool",
                    "starting_policy_failure_rate": support_failures / support_episodes,
                    "starting_policy_failure_rate_unit": "fraction_of_scoring_rollouts",
                    "score_missingness_rate": measurements["measurement"]["score_missingness_rate"],
                    "score_missingness_rate_unit": "fraction_of_expected_scores",
                    "frozen_point_prediction": candidate_id == measurements["decision"],
                    "candidate_outcomes_opened": False,
                },
            )
        )
    for output, profile in zip(outputs, profiles, strict=True):
        write_profile_input(output, profile, force=force)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--qualification", type=Path, default=DEFAULT_QUALIFICATION)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = export_profiles(
        measurements_path=args.measurements,
        protocol_path=args.protocol,
        sources_path=args.sources,
        qualification_path=args.qualification,
        output_dir=args.output_dir,
        force=args.force,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
