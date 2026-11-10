#!/usr/bin/env python3
"""Export Vero development measurements as domain-preserving profiles."""

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

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULT = (
    ROOT / "data/formal-verification/vero/results/development-policy-measurement.v1.json"
)
DEFAULT_PROTOCOL = ROOT / "data/formal-verification/vero/policy-probe-protocol.v5.json"
DEFAULT_SOURCE_PIN = ROOT / "data/formal-verification/vero/source-pin.json"
CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/formal-verification-grouped-probe-v1.md"
)
ADAPTER_ID = "formal-verification.vero-development-probe"
ADAPTER_REVISION = "v1"


class AdapterError(ValueError):
    """Raised when Vero artifacts cannot support an exact profile export."""


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


def validate_inputs(
    result: dict[str, Any],
    protocol: dict[str, Any],
    source: dict[str, Any],
    protocol_path: Path,
) -> None:
    if result.get("schema_version") != "anarres.formal-verification-development-result.v1":
        raise AdapterError("unsupported Vero result schema")
    if result.get("status") != "complete_negative_development_measurement":
        raise AdapterError("Vero development result is not complete")
    if protocol.get("schema_version") != "anarres.formal-verification-policy-probe.v5":
        raise AdapterError("result requires the v5 policy-probe contract")
    for field in ("source_id", "repository", "commit", "license"):
        value = source.get(field)
        if not isinstance(value, str) or not value.strip():
            raise AdapterError(f"source pin is missing a nonempty {field}")
    frozen = result.get("frozen_inputs", {}).get("policy_probe_protocol", {})
    if frozen.get("sha256") != sha256(protocol_path):
        raise AdapterError("result does not match the checked-in policy-probe protocol")
    if protocol["source"]["vero_id"] != source.get("source_id"):
        raise AdapterError("source revision differs between protocol and source pin")
    if result["scope"].get("qualification_and_prospective_repositories_opened") is not False:
        raise AdapterError("development result opened a protected repository split")
    execution = result["execution"]
    if execution.get("attempts") != 32 or execution.get("fresh_grade_builds") != 32:
        raise AdapterError("Vero result is missing expected attempts or fresh grades")
    if execution.get("infrastructure_valid_attempts") != 32:
        raise AdapterError("not every Vero attempt is infrastructure-valid")
    if execution.get("infrastructure_errors") != 0:
        raise AdapterError("Vero result contains infrastructure errors")
    modes = result["measurement"].get("by_mode", {})
    if set(modes) != {"proof", "codeproof"}:
        raise AdapterError("Vero result must contain exactly proof and codeproof modes")
    measurement = result["measurement"]
    if measurement.get("strict_successes") != 0 or measurement.get("strict_trials", 0) <= 0:
        raise AdapterError("negative Vero result has inconsistent strict-verification totals")
    if measurement.get("passes_preregistered_support_gate") is not False:
        raise AdapterError("negative Vero result unexpectedly passes the support gate")
    mode_tokens = 0
    for mode, values in modes.items():
        if values.get("model_tokens", 0) <= 0 or values.get("specification_groups", 0) <= 0:
            raise AdapterError(f"{mode} has an invalid cost or group count")
        coordinates = (
            values.get("rho_per_million_model_tokens"),
            values.get("effective_coverage_H"),
        )
        if any(
            not isinstance(value, (int, float)) or not math.isfinite(value) for value in coordinates
        ):
            raise AdapterError(f"{mode} contains a nonfinite coordinate")
        mode_tokens += values["model_tokens"]
    if mode_tokens != execution.get("model_tokens"):
        raise AdapterError("mode token totals do not match the execution total")


def export_profiles(
    *,
    result_path: Path,
    protocol_path: Path,
    source_pin_path: Path,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Export one profile per Vero proof mode from the released measurement."""

    result = read_object(result_path)
    protocol = read_object(protocol_path)
    source = read_object(source_pin_path)
    validate_inputs(result, protocol, source, protocol_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    policy = protocol["starting_policy"]
    source_revision = source["commit"]
    attempts_per_mode = result["execution"]["attempts"] // 2
    support_passed = result["measurement"]["passes_preregistered_support_gate"]
    outputs = [
        output_dir / "vero-development-proof-v5.profile-input.json",
        output_dir / "vero-development-codeproof-v5.profile-input.json",
    ]
    if not force:
        existing = [path for path in outputs if path.exists()]
        if existing:
            raise FileExistsError(existing[0])
    profiles = []
    for mode in ("proof", "codeproof"):
        measured = result["measurement"]["by_mode"][mode]
        groups = int(measured["specification_groups"])
        model_tokens = int(measured["model_tokens"])
        profile = build_profile_input(
            environment_id=f"vero-development-{mode}-v5",
            domain="formal-verification",
            subject={
                "kind": "policy-agent",
                "id": f"{policy['model_id']}+{policy['agent_scaffold']}",
                "revision": (
                    f"model:{policy['model_revision']}|agent:{policy['agent_scaffold_revision']}"
                ),
            },
            producer={
                "kind": "domain-adapter",
                "id": ADAPTER_ID,
                "revision": ADAPTER_REVISION,
            },
            source={
                "uri": source["repository"],
                "revision": source_revision,
                "license": source["license"],
            },
            measurement_contract={
                "kind": "repeated-machine-checked-policy-probe",
                "id": f"{protocol['protocol_id']}:{mode}",
                "revision": "v5",
                "repetitions": protocol["probe_design"]["independent_attempts_per_repository_mode"],
                "cost_unit": "model_tokens",
            },
            qualification_checks=[
                qualification_check(
                    check_id="infrastructure-valid",
                    category="infrastructure",
                    status="pass",
                    severity="error",
                    summary="Every attempt completed fresh grading without infrastructure error.",
                ),
                qualification_check(
                    check_id="protected-splits-sealed",
                    category="source",
                    status="pass",
                    severity="error",
                    summary="Qualification and prospective repositories remained unopened.",
                ),
                qualification_check(
                    check_id="preregistered-support",
                    category="measurement",
                    status="pass" if support_passed else "fail",
                    severity="error",
                    summary=(
                        "The measurement passed the preregistered support gate."
                        if support_passed
                        else (
                            "No strict verified support was observed; ranking and training "
                            "remain unauthorized."
                        )
                    ),
                ),
            ],
            coordinates=[
                coordinate(
                    name="usable_signal_density",
                    definition_uri=CONVENTION_URI,
                    definition_revision="v1-development",
                    role="signal",
                    value=float(measured["rho_per_million_model_tokens"]),
                    unit="advantage_mass_per_million_model_tokens",
                    direction="contextual",
                    estimator="leave-one-out absolute strict-reward advantage mass",
                    sample_count=groups,
                ),
                coordinate(
                    name="effective_verification_coverage",
                    definition_uri=CONVENTION_URI,
                    definition_revision="v1-development",
                    role="coverage",
                    value=float(measured["effective_coverage_H"]),
                    unit="fraction",
                    direction="contextual",
                    estimator="normalized effective sample size over specification groups",
                    sample_count=groups,
                ),
                coordinate(
                    name="mean_model_tokens_per_attempt",
                    definition_uri=CONVENTION_URI,
                    definition_revision="v1-development",
                    role="cost",
                    value=model_tokens / attempts_per_mode,
                    unit="model_tokens_per_attempt",
                    direction="lower",
                    estimator="arithmetic mean over infrastructure-valid attempts",
                    sample_count=attempts_per_mode,
                ),
            ],
            artifacts=[
                local_artifact(
                    role="native-measurements",
                    path=result_path,
                    uri="repo://data/formal-verification/vero/results/development-policy-measurement.v1.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                    producing_run=result["result_id"],
                ),
                local_artifact(
                    role="measurement-contract",
                    path=protocol_path,
                    uri="repo://data/formal-verification/vero/policy-probe-protocol.v5.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                ),
                local_artifact(
                    role="source-pin",
                    path=source_pin_path,
                    uri="repo://data/formal-verification/vero/source-pin.json",
                    media_type="application/json",
                    license_id="Apache-2.0",
                ),
            ],
            attributes={
                "mode": mode,
                "repositories": len(result["scope"]["repositories"]),
                "attempts": attempts_per_mode,
                "pooled_strict_successes": result["measurement"]["strict_successes"],
                "support_gate_passed": support_passed,
            },
        )
        profiles.append(profile)
    for output, profile in zip(outputs, profiles, strict=True):
        write_profile_input(output, profile, force=force)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--source-pin", type=Path, default=DEFAULT_SOURCE_PIN)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    outputs = export_profiles(
        result_path=args.result,
        protocol_path=args.protocol,
        source_pin_path=args.source_pin,
        output_dir=args.output_dir,
        force=args.force,
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
