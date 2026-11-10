#!/usr/bin/env python3
"""Export the released finance starting-policy qualification as a profile."""

from __future__ import annotations

import argparse
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
STUDY = ROOT / "experiments/finance/environment-selection"
DEFAULT_RESULT = STUDY / "QWEN3_8B_QUALIFICATION.json"
DEFAULT_PROTOCOL = STUDY / "PROTOCOL.json"
DEFAULT_PREFLIGHT = STUDY / "PREFLIGHT.json"
DEFAULT_SOURCES = STUDY / "SOURCES.json"
DEFAULT_HARNESS = STUDY / "adapters/business_bench_openai_policy.py"

CONVENTION_URI = (
    "https://github.com/anarres-organization/anarres/blob/main/"
    "docs/conventions/finance-operations-policy-qualification-v1.md"
)
ADAPTER_ID = "agentic-finance.business-bench-policy-qualification"
ADAPTER_REVISION = "v1"
MODEL_ID = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
EXPECTED_POLICY_ID = "qwen3-8b-b968826d9c46"
OUTPUT_NAME = "business-bench-qwen3-8b-development.profile-input.json"


class AdapterError(ValueError):
    """Raised when released finance evidence cannot support an exact profile."""


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AdapterError(f"required native artifact does not exist: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdapterError(f"expected an object in {path}")
    return value


def _finite_rate(record: dict[str, Any], name: str) -> float:
    value = record.get(name)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise AdapterError(f"{name} is missing or nonnumeric")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise AdapterError(f"{name} must be a finite fraction")
    return number


def _nonnegative_integer(record: dict[str, Any], name: str) -> int:
    value = record.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdapterError(f"{name} must be a nonnegative integer")
    return value


def _recover_proportion_count(rate: float, denominator: int, name: str) -> int:
    """Recover the integer numerator represented by a released six-decimal rate."""

    numerator = round(rate * denominator)
    if denominator <= 0 or round(numerator / denominator, 6) != rate:
        raise AdapterError(f"{name} is inconsistent with its released denominator")
    return numerator


def business_bench_source(sources: dict[str, Any]) -> dict[str, Any]:
    rows = sources.get("sources")
    if not isinstance(rows, list):
        raise AdapterError("finance source registry is missing its sources array")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == "business_bench"]
    if len(matches) != 1:
        raise AdapterError("finance source registry must contain one Business Bench record")
    return matches[0]


def validate_inputs(
    result: dict[str, Any],
    protocol: dict[str, Any],
    preflight: dict[str, Any],
    sources: dict[str, Any],
) -> dict[str, Any]:
    if result.get("status") != "qualification_complete":
        raise AdapterError("finance qualification result is not complete")
    if result.get("policy_id") != EXPECTED_POLICY_ID:
        raise AdapterError("finance qualification result has an unexpected policy revision")
    if protocol.get("study_id") != "prospective_finance_environment_selection_v1":
        raise AdapterError("unsupported finance measurement protocol")

    source = business_bench_source(sources)
    source_revision = source.get("revision")
    if not isinstance(source_revision, str) or not source_revision:
        raise AdapterError("Business Bench source revision is missing")
    if source_revision != protocol.get("source", {}).get("revision"):
        raise AdapterError("Business Bench revision differs between protocol and registry")
    if source_revision != preflight.get("source_revision"):
        raise AdapterError("Business Bench revision differs between preflight and registry")
    if source.get("license") != "MIT":
        raise AdapterError("Business Bench license is absent or unexpected")
    if preflight.get("scientific_outcomes_opened") is not False:
        raise AdapterError("source preflight opened scientific outcomes")
    if preflight.get("passed_trials") != preflight.get("workflow_seed_trials"):
        raise AdapterError("Business Bench source preflight is incomplete")

    expected = _nonnegative_integer(result, "expected_episodes")
    recorded = _nonnegative_integer(result, "recorded_episodes")
    valid = _nonnegative_integer(result, "valid_episodes")
    failures = _nonnegative_integer(result, "infrastructure_failures")
    if expected != 128 or recorded != expected:
        raise AdapterError("qualification result does not contain all 128 planned episodes")
    if valid + failures != recorded:
        raise AdapterError("valid and infrastructure-invalid episode counts do not reconcile")

    complete_groups = _nonnegative_integer(result, "complete_scenario_groups")
    mixed_groups = _nonnegative_integer(result, "mixed_scenario_groups")
    if complete_groups <= 0 or mixed_groups > complete_groups:
        raise AdapterError("scenario-group counts are incomplete or inconsistent")

    tool_valid_rate = _finite_rate(result, "tool_protocol_valid_rate")
    tool_valid_episodes = _recover_proportion_count(
        tool_valid_rate, valid, "tool_protocol_valid_rate"
    )
    completion_rate = _finite_rate(result, "completion_rate")
    _recover_proportion_count(completion_rate, tool_valid_episodes, "completion_rate")
    mixed_fraction = _finite_rate(result, "mixed_group_fraction")
    if round(mixed_groups / complete_groups, 6) != mixed_fraction:
        raise AdapterError("mixed_group_fraction is inconsistent with scenario-group counts")
    _finite_rate(result, "material_control_violation_rate")
    _finite_rate(result, "truncation_rate")

    for name in ("median_generated_tokens", "median_tool_calls"):
        value = result.get(name)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise AdapterError(f"{name} is missing or nonnumeric")
        if not math.isfinite(float(value)) or float(value) < 0:
            raise AdapterError(f"{name} must be finite and nonnegative")

    gates = result.get("gates")
    required_gates = {
        "planned_episode_completeness",
        "tool_protocol_valid_rate_at_least_0_98",
        "completion_rate_between_0_02_and_0_80",
        "mixed_group_fraction_at_least_0_10",
        "at_least_two_workflows_with_mixed_groups",
        "truncation_rate_at_most_0_10",
    }
    if not isinstance(gates, dict) or set(gates) != required_gates:
        raise AdapterError("qualification result has an incomplete gate record")
    if any(not isinstance(value, bool) for value in gates.values()):
        raise AdapterError("qualification gate states must be boolean")
    if result.get("qualified") is not all(gates.values()):
        raise AdapterError("qualification decision does not match the released gates")
    return source


def _gate_check(gates: dict[str, bool], gate_id: str, summary: str) -> dict[str, str]:
    passed = gates[gate_id]
    return qualification_check(
        check_id=gate_id.replace("_", "-"),
        category="measurement",
        status="pass" if passed else "fail",
        severity="error",
        summary=summary,
    )


def export_profile(
    *,
    result_path: Path,
    protocol_path: Path,
    preflight_path: Path,
    sources_path: Path,
    harness_path: Path,
    output_dir: Path,
    force: bool = False,
) -> Path:
    """Export one profile from the released Qwen3-8B qualification record."""

    result = read_object(result_path)
    protocol = read_object(protocol_path)
    preflight = read_object(preflight_path)
    sources = read_object(sources_path)
    source = validate_inputs(result, protocol, preflight, sources)
    if not harness_path.is_file():
        raise AdapterError(f"required native artifact does not exist: {harness_path}")

    valid = int(result["valid_episodes"])
    tool_valid_rate = float(result["tool_protocol_valid_rate"])
    tool_valid_episodes = _recover_proportion_count(
        tool_valid_rate, valid, "tool_protocol_valid_rate"
    )
    complete_groups = int(result["complete_scenario_groups"])
    gates = result["gates"]
    infrastructure_failures = int(result["infrastructure_failures"])

    profile = build_profile_input(
        environment_id="business-bench-finance-operations-qwen3-8b-development",
        domain="agentic-finance",
        subject={"kind": "policy", "id": MODEL_ID, "revision": MODEL_REVISION},
        producer={"kind": "domain-adapter", "id": ADAPTER_ID, "revision": ADAPTER_REVISION},
        source={
            "uri": source["url"],
            "revision": source["revision"],
            "license": source["license"],
        },
        measurement_contract={
            "kind": "repeated-finance-operation-policy-qualification",
            "id": "finance.business-bench-starting-policy-qualification.v1",
            "revision": "v1",
            "repetitions": 4,
            "cost_unit": "generated_tokens",
        },
        qualification_checks=[
            qualification_check(
                check_id="source-generator-preflight",
                category="source",
                status="pass",
                severity="error",
                summary="All 20 workflow-by-seed generator preflight trials passed.",
            ),
            qualification_check(
                check_id="planned-episode-accounting",
                category="infrastructure",
                status="pass",
                severity="error",
                summary="All 128 planned episodes have a recorded outcome or failure state.",
            ),
            qualification_check(
                check_id="infrastructure-failures-present",
                category="infrastructure",
                status="fail" if infrastructure_failures else "pass",
                severity="warning",
                summary=(
                    f"{infrastructure_failures} episodes were infrastructure-invalid and remain "
                    "separate from finance-task failures."
                    if infrastructure_failures
                    else "No infrastructure-invalid episodes were observed."
                ),
            ),
            _gate_check(
                gates,
                "tool_protocol_valid_rate_at_least_0_98",
                "At least 98% of infrastructure-valid episodes must satisfy the tool protocol.",
            ),
            _gate_check(
                gates,
                "completion_rate_between_0_02_and_0_80",
                "Executable completion must lie between 2% and 80% on development scenarios.",
            ),
            _gate_check(
                gates,
                "mixed_group_fraction_at_least_0_10",
                "At least 10% of complete scenario groups must contain mixed outcomes.",
            ),
            _gate_check(
                gates,
                "at_least_two_workflows_with_mixed_groups",
                "At least two workflow families must contain a mixed scenario group.",
            ),
            _gate_check(
                gates,
                "truncation_rate_at_most_0_10",
                "No more than 10% of infrastructure-valid episodes may truncate.",
            ),
        ],
        coordinates=[
            coordinate(
                name="tool_protocol_valid_rate",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="reliability",
                value=tool_valid_rate,
                unit="fraction",
                direction="higher",
                estimator="proportion over infrastructure-valid episodes",
                sample_count=valid,
            ),
            coordinate(
                name="executable_completion_rate",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="signal",
                value=float(result["completion_rate"]),
                unit="fraction",
                direction="contextual",
                estimator="proportion over tool-protocol-valid episodes",
                sample_count=tool_valid_episodes,
            ),
            coordinate(
                name="mixed_scenario_group_fraction",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="coverage",
                value=float(result["mixed_group_fraction"]),
                unit="fraction",
                direction="contextual",
                estimator="proportion over complete repeated-attempt scenario groups",
                sample_count=complete_groups,
            ),
            coordinate(
                name="material_control_violation_rate",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="finance.control",
                value=float(result["material_control_violation_rate"]),
                unit="fraction",
                direction="lower",
                estimator="proportion over infrastructure-valid episodes",
                sample_count=valid,
            ),
            coordinate(
                name="truncation_rate",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="reliability",
                value=float(result["truncation_rate"]),
                unit="fraction",
                direction="lower",
                estimator="proportion over infrastructure-valid episodes",
                sample_count=valid,
            ),
            coordinate(
                name="median_generated_tokens_per_episode",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="cost",
                value=float(result["median_generated_tokens"]),
                unit="generated_tokens_per_episode",
                direction="contextual",
                estimator="median over infrastructure-valid episodes",
                sample_count=valid,
            ),
            coordinate(
                name="median_tool_calls_per_episode",
                definition_uri=CONVENTION_URI,
                definition_revision="v1-development",
                role="cost",
                value=float(result["median_tool_calls"]),
                unit="tool_calls_per_episode",
                direction="contextual",
                estimator="median over infrastructure-valid episodes",
                sample_count=valid,
            ),
        ],
        artifacts=[
            local_artifact(
                role="native-measurements",
                path=result_path,
                uri="repo://experiments/finance/environment-selection/QWEN3_8B_QUALIFICATION.json",
                media_type="application/json",
                license_id="Apache-2.0",
            ),
            local_artifact(
                role="measurement-contract",
                path=protocol_path,
                uri="repo://experiments/finance/environment-selection/PROTOCOL.json",
                media_type="application/json",
                license_id="Apache-2.0",
            ),
            local_artifact(
                role="source-preflight",
                path=preflight_path,
                uri="repo://experiments/finance/environment-selection/PREFLIGHT.json",
                media_type="application/json",
                license_id="Apache-2.0",
            ),
            local_artifact(
                role="source-registry",
                path=sources_path,
                uri="repo://experiments/finance/environment-selection/SOURCES.json",
                media_type="application/json",
                license_id="Apache-2.0",
            ),
            local_artifact(
                role="agent-harness",
                path=harness_path,
                uri=(
                    "repo://experiments/finance/environment-selection/adapters/"
                    "business_bench_openai_policy.py"
                ),
                media_type="text/x-python",
                license_id="Apache-2.0",
            ),
        ],
        attributes={
            "expected_episodes": int(result["expected_episodes"]),
            "recorded_episodes": int(result["recorded_episodes"]),
            "valid_episodes": valid,
            "infrastructure_failures": infrastructure_failures,
            "complete_scenario_groups": complete_groups,
            "mixed_scenario_groups": int(result["mixed_scenario_groups"]),
            "qualified": bool(result["qualified"]),
        },
    )
    output = output_dir / OUTPUT_NAME
    write_profile_input(output, profile, force=force)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--harness", type=Path, default=DEFAULT_HARNESS)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = export_profile(
        result_path=args.result,
        protocol_path=args.protocol,
        preflight_path=args.preflight,
        sources_path=args.sources,
        harness_path=args.harness,
        output_dir=args.output_dir,
        force=args.force,
    )
    print(output)


if __name__ == "__main__":
    main()
