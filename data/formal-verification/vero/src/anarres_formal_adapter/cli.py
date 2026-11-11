"""CLI for the released negative Vero development measurement."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from anarres.core import consume_adapter_invocation, load_source_manifest

from anarres_formal_adapter import source_qualification


class FormalCliError(ValueError):
    """Raised when released Vero evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "formal",
        "version": "0.2.0",
        "protocol_version": 2,
        "domain": "formal-verification",
        "executable": "anarres-formal",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "profile",
            "qualification-report",
            "source-qualification",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "vero-leanstral-development-probe-v5:codeproof",
            "vero-leanstral-development-probe-v5:proof",
        ],
        "source_formats": ["vero-checkout-v1"],
    }


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Validate the exact released Vero checkout without running Lean or a policy."""

    descriptor = adapter_descriptor()
    source = load_source_manifest(
        args.manifest,
        expected_adapter="formal",
        expected_version=descriptor["version"],
        expected_domain=descriptor["domain"],
        accepted_formats=tuple(descriptor["source_formats"]),
    )
    pin = source_qualification.load_source_pin()
    expected_revision = f"git:{pin['commit']}"
    if source.revision != expected_revision:
        raise FormalCliError(
            f"manifest revision must identify the released Vero commit {expected_revision}"
        )
    if source.license != pin["license"]:
        raise FormalCliError(
            "manifest license must preserve Vero's benchmark-specific upstream licenses"
        )
    report = source_qualification.qualify(source.source)
    return {
        "status": "qualified",
        "qualification_state": "source_qualified_runtime_pending",
        "environment_id": source.environment_id,
        "native_format": source.native_format,
        "source_id": report["source_id"],
        "source_revision": source.revision,
        "source_license": source.license,
        "source_pin_sha256": f"sha256:{report['source_pin_sha256']}",
        "benchmark_tree_git_oid": report["benchmark_tree_git_oid"],
        "benchmarks": report["counts"]["benchmarks"],
        "modules": report["counts"]["modules"],
        "apis": report["counts"]["apis"],
        "specifications": report["counts"]["specs"],
        "source_languages": report["counts"]["source_languages"],
        "lean_version": report["lean_version"],
        "modes": report["modes"],
        "verified_core_artifacts": report["verified_artifacts"],
        "runtime_qualified": False,
        "policy_probe_available": False,
        "model_execution_started": False,
        "qualification_or_prospective_tasks_opened": False,
    }


def repository_root(explicit: Path | None = None) -> Path:
    """Resolve an explicit checkout or one containing the current directory."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    relative = Path("data/formal-verification/vero/export_environment_profiles.py")
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / relative).is_file():
                return candidate
    raise FormalCliError(
        "Anarres repository not found. Pass --repository with a released checkout."
    )


def study_root(repository: Path) -> Path:
    return repository / "data/formal-verification/vero"


def load_native_adapter(repository: Path) -> ModuleType:
    path = study_root(repository) / "export_environment_profiles.py"
    specification = importlib.util.spec_from_file_location(
        "anarres_formal_vero_native_adapter", path
    )
    if specification is None or specification.loader is None:
        raise FormalCliError(f"cannot load the released Vero adapter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_module(path: Path, name: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise FormalCliError(f"cannot load released formal-verification code: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def native_paths(repository: Path) -> dict[str, Path]:
    root = study_root(repository)
    return {
        "result": root / "results/development-policy-measurement.v1.json",
        "protocol": root / "policy-probe-protocol.v5.json",
        "source": root / "source-pin.json",
    }


def qualification_paths(repository: Path) -> dict[str, Path]:
    root = study_root(repository)
    return {
        "result": root / "results/development-policy-qualification.codex-sol-v1.json",
        "protocol": root / "policy-codex-sol-qualification.v1.json",
        "execution": root / "policy-codex-sol-execution.v1.json",
        "infrastructure_retry": root / "policy-codex-sol-infrastructure-retry.v1.json",
    }


def validate_native(repository: Path) -> tuple[ModuleType, dict[str, Any]]:
    native = load_native_adapter(repository)
    paths = native_paths(repository)
    result = native.read_object(paths["result"])
    protocol = native.read_object(paths["protocol"])
    source = native.read_object(paths["source"])
    native.validate_inputs(result, protocol, source, paths["protocol"])
    return native, {"result": result, "protocol": protocol, "source": source}


def validate_qualification(repository: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    paths = qualification_paths(repository)
    records = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
    result = records["result"]
    protocol = records["protocol"]

    validator = load_module(
        study_root(repository) / "validate_codex_qualification.py",
        "anarres_formal_codex_qualification_validator",
    )
    validator.validate(protocol, study_root(repository))

    if (
        result.get("schema_version")
        != "anarres.formal-verification-development-qualification-result.v1"
    ):
        raise FormalCliError("unsupported GPT-5.6 qualification result schema")
    if result.get("status") != "complete_support_pass_with_containment_followup":
        raise FormalCliError("GPT-5.6 qualification result has an unexpected status")

    frozen = result.get("frozen_inputs", {})
    frozen_paths = {
        "qualification_protocol": paths["protocol"],
        "execution_record": paths["execution"],
        "infrastructure_retry_record": paths["infrastructure_retry"],
    }
    for name, path in frozen_paths.items():
        if frozen.get(name, {}).get("sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
            raise FormalCliError(f"{name} hash disagrees with the qualification result")

    execution = result["execution"]
    design = protocol["qualification_design"]
    policy = protocol["starting_policy"]
    if (
        execution["source_id"] != protocol["source"]["vero_id"]
        or execution["benchmark_id"] != design["benchmark_id"]
        or execution["mode"] != design["mode"]
        or execution["starting_policy"] != policy["model_id"]
        or execution["agent_harness"]
        != f"{policy['agent_harness']}@{policy['agent_harness_version']}"
        or execution["reasoning_effort"] != policy["reasoning_effort"]
        or execution["independent_attempts"] != design["independent_attempts"]
        or execution["scientific_retries"] != design["scientific_retry_count"]
    ):
        raise FormalCliError("qualification execution differs from its frozen protocol")

    grade = result["fresh_grade"]
    if (
        not grade["build_ok"]
        or grade["total_specifications"] != 9
        or grade["passed_specifications"] != 9
        or grade["failed_specifications"] != 0
        or grade["unfilled_specifications"] != 0
        or grade["overfilled_specifications"] != 0
        or grade["filled_slot_taint_count"] != 0
        or grade["approved_axiom_check"] != "pass"
        or grade["unexpected_marker_count"] != 0
        or not result["decision"]["passes_support_threshold"]
    ):
        raise FormalCliError("qualification result does not preserve the strict 9/9 support pass")

    containment = result["containment_audit"]
    if (
        containment["task_network_access"]
        or containment["qualification_and_prospective_repositories_opened"]
        or containment["reference_solution_access_observed"]
        or not containment["fresh_grade_retained_only_editable_slots"]
        or not containment["generic_upstream_guidance_readable"]
        or not containment["write_outside_rendered_task_observed"]
    ):
        raise FormalCliError("qualification containment boundary changed")
    return result, paths


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    _, records = validate_native(repository)
    validate_qualification(repository)
    result = records["result"]
    measurement = result["measurement"]
    execution = result["execution"]
    modes = measurement["by_mode"]
    return {
        "study_id": result["result_id"],
        "domain": "formal-verification",
        "status": result["status"],
        "attempts": execution["attempts"],
        "infrastructure_valid_attempts": execution["infrastructure_valid_attempts"],
        "infrastructure_errors": execution["infrastructure_errors"],
        "strict_successes": measurement["strict_successes"],
        "strict_trials": measurement["strict_trials"],
        "support_gate_passed": measurement["passes_preregistered_support_gate"],
        "qualification_and_prospective_repositories_opened": result["scope"][
            "qualification_and_prospective_repositories_opened"
        ],
        "mode_measurements": {
            mode: {
                "usable_signal_density": values["rho_per_million_model_tokens"],
                "effective_verification_coverage": values["effective_coverage_H"],
                "model_tokens": values["model_tokens"],
            }
            for mode, values in sorted(modes.items())
        },
        "profile_ready": False,
        "candidate_ranking_authorized": False,
        "downstream_training_authorized": False,
        "qualification_report_available": True,
        "native_source_format": "vero-checkout-v1",
        "native_source_qualification_available": True,
        "policy_probe_available": False,
        "next_required_gate": "task-only containment requalification before repeated measurement",
    }


def export_profiles(repository: Path, output_dir: Path, force: bool = False) -> list[Path]:
    native, _ = validate_native(repository)
    paths = native_paths(repository)
    return native.export_profiles(
        result_path=paths["result"],
        protocol_path=paths["protocol"],
        source_pin_path=paths["source"],
        output_dir=output_dir,
        force=force,
    )


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    outputs = export_profiles(repository, args.output_dir, force=args.force)
    return {
        "status": "exported_negative_measurement",
        "profile_count": len(outputs),
        "profiles_ready": False,
        "candidate_ranking_authorized": False,
        "downstream_training_authorized": False,
        "outputs": [str(path) for path in outputs],
    }


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def command_qualification(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    result, paths = validate_qualification(repository)
    execution = result["execution"]
    grade = result["fresh_grade"]
    containment = result["containment_audit"]
    return {
        "schema_version": "anarres.formal-verification-qualification-report.v1",
        "status": "released_reproduced",
        "study_id": result["result_id"],
        "role": "separate_development_support_qualification",
        "profile_input": False,
        "starting_policy": {
            "model": execution["starting_policy"],
            "agent_harness": execution["agent_harness"],
            "reasoning_effort": execution["reasoning_effort"],
        },
        "task": {
            "source_id": execution["source_id"],
            "benchmark_id": execution["benchmark_id"],
            "mode": execution["mode"],
            "lean_version": execution["lean_version"],
            "lean_commit": execution["lean_commit"],
        },
        "strict_support": {
            "independent_attempts": execution["independent_attempts"],
            "total_specifications": grade["total_specifications"],
            "passed_specifications": grade["passed_specifications"],
            "support_threshold_passed": result["decision"]["passes_support_threshold"],
        },
        "realized_cost": {
            "wall_seconds": execution["wall_seconds"],
            "tool_calls": execution["tool_calls"],
            "input_tokens": execution["input_tokens"],
            "cached_input_tokens": execution["cached_input_tokens"],
            "output_tokens": execution["output_tokens"],
            "reasoning_output_tokens": execution["reasoning_output_tokens"],
        },
        "containment": {
            "task_network_access": containment["task_network_access"],
            "protected_repositories_opened": containment[
                "qualification_and_prospective_repositories_opened"
            ],
            "reference_solution_access_observed": containment["reference_solution_access_observed"],
            "fresh_grade_retained_only_editable_slots": containment[
                "fresh_grade_retained_only_editable_slots"
            ],
            "task_only_boundary_passed": False,
            "followup_required": True,
        },
        "decision": {
            "repeated_measurement_authorized": False,
            "candidate_ranking_authorized": False,
            "downstream_training_authorized": False,
            "next_step": result["decision"]["next_step"],
        },
        "claim_boundary": result["scientific_role"],
        "artifacts": {name: digest(path) for name, path in sorted(paths.items())},
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    qualification, qualification_paths_by_role = validate_qualification(repository)
    with (
        tempfile.TemporaryDirectory(prefix="anarres-formal-verify-a-") as first,
        tempfile.TemporaryDirectory(prefix="anarres-formal-verify-b-") as second,
    ):
        first_outputs = export_profiles(repository, Path(first))
        second_outputs = export_profiles(repository, Path(second))
        first_bytes = {path.name: path.read_bytes() for path in first_outputs}
        second_bytes = {path.name: path.read_bytes() for path in second_outputs}
        if first_bytes != second_bytes:
            raise FormalCliError("Vero profile export is not deterministic")
        profiles = [json.loads(payload) for payload in first_bytes.values()]
        for profile in profiles:
            checks = {
                check["check_id"]: check["status"] for check in profile["qualification_checks"]
            }
            values = {item["name"]: item["value"] for item in profile["coordinates"]}
            if checks.get("infrastructure-valid") != "pass":
                raise FormalCliError("infrastructure-valid qualification was not preserved")
            if checks.get("preregistered-support") != "fail":
                raise FormalCliError("failed support qualification was not preserved")
            if values.get("usable_signal_density") != 0.0:
                raise FormalCliError("zero usable signal was not preserved")
            if values.get("effective_verification_coverage") != 0.0:
                raise FormalCliError("zero verification coverage was not preserved")
            if values.get("mean_model_tokens_per_attempt", 0.0) <= 0.0:
                raise FormalCliError("positive model cost was not preserved")
        digests = {
            path.name: digest(path)
            for path in sorted(first_outputs, key=lambda output: output.name)
        }
    return {
        "status": "pass",
        "profile_count": len(digests),
        "profile_digests": digests,
        "profiles_ready": False,
        "candidate_ranking_authorized": False,
        "downstream_training_authorized": False,
        "qualification_result_digest": digest(qualification_paths_by_role["result"]),
        "qualification_support_passed": qualification["decision"]["passes_support_threshold"],
        "repeated_measurement_authorized": False,
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres formal",
        description="Inspect and export the released negative Vero development measurement.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    qualify_source = commands.add_parser(
        "qualify-source", help="Validate the exact pinned Vero source checkout."
    )
    qualify_source.add_argument("--manifest", type=Path, required=True)
    qualify_source.add_argument("--json", action="store_true")
    qualify_source.set_defaults(handler=command_qualify_source)

    status = commands.add_parser("status", help="Show support and authorization status.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export the native Vero profile inputs.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    qualification = commands.add_parser(
        "qualification",
        help="Report the separate GPT-5.6 development support qualification.",
    )
    add_common(qualification)
    qualification.set_defaults(handler=command_qualification)

    verify = commands.add_parser("verify", help="Verify deterministic negative profiles.")
    add_common(verify)
    verify.set_defaults(handler=command_verify)
    return result


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<42} {rendered}")


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="formal")
        arguments = parser().parse_args(raw_arguments)
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except FileExistsError as error:
        path = error.filename or (error.args[0] if error.args else "output")
        print(f"error: output already exists: {path}", file=sys.stderr)
        raise SystemExit(1) from error
    except (FormalCliError, ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
