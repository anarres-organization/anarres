"""CLI for the released negative Vero development measurement."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

from anarres.core import consume_adapter_invocation, load_source_manifest

from anarres_formal_adapter import runtime_qualification, source_qualification

REPEATED_MEASUREMENT_AUTHORIZATION = "execution-authorization.codex-sol-v2.json"
REPEATED_MEASUREMENT_RELEASE = "results/repeated-measurement.codex-sol-v2"


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
            "runtime-qualification",
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


def qualified_source(manifest: Path) -> tuple[Any, dict[str, Any]]:
    """Load and qualify the exact released Vero source manifest."""
    descriptor = adapter_descriptor()
    source = load_source_manifest(
        manifest,
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
    return source, source_qualification.qualify(source.source)


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Validate the exact released Vero checkout without running Lean or a policy."""

    source, report = qualified_source(args.manifest)
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


def command_qualify_runtime(args: argparse.Namespace) -> dict[str, Any]:
    """Validate a source-bound execution contract without contacting a model."""

    source, source_report = qualified_source(args.manifest)
    report = runtime_qualification.qualify(
        contract_path=args.runtime,
        source=source.source,
        source_report=source_report,
        source_revision=source.revision,
        lean_executable=args.lean_executable,
        lake_executable=args.lake_executable,
    )
    if args.output is not None:
        if args.output.exists() and not args.force:
            raise FileExistsError(args.output)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report = {**report, "output": str(args.output)}
    return report


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


def task_boundary_status(repository: Path) -> dict[str, Any]:
    """Report the task-only execution boundary separately from source and runtime gates."""

    path = study_root(repository) / "containment-contract-codex-sol.v4.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    validator = load_module(
        study_root(repository) / "validate_task_boundary_receipt.py",
        "anarres_formal_task_boundary_validator",
    )
    required = validator.validate_contract(contract)
    # The frozen contract never changes. Qualification comes only from a released
    # receipt that validates against it and against the route files in this checkout.
    receipt_path = study_root(repository) / contract["released_receipt"]
    receipt = None
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        validator.validate_receipt(
            receipt,
            contract,
            hashlib.sha256(path.read_bytes()).hexdigest(),
            bundle=receipt_path.parent,
        )
        validator.validate_route_files(receipt, study_root(repository))
    return {
        "contract_id": contract["contract_id"],
        "contract_sha256": digest(path),
        "contract_status": contract["status"],
        "required_tests": len(required),
        "receipt_released": receipt is not None,
        "receipt_id": receipt["receipt_id"] if receipt else None,
        "runtime_image": receipt["runtime_image"]["reference"] if receipt else None,
        "qualified": bool(receipt and receipt["qualified"]),
        "reported_separately_from": ["source-qualification", "runtime-qualification"],
    }


def repeated_measurement_status(repository: Path) -> dict[str, Any]:
    """Validate the frozen repeated-measurement protocol and its outcome-blind queue."""

    root = study_root(repository)
    protocol_path = root / "policy-probe-protocol.codex-sol-v2.json"
    queue_path = root / "probe-queue.codex-sol-v2.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    validator = load_module(
        root / "validate_codex_sol_probe_protocol.py", "anarres_formal_repeated_validator"
    )
    validator.validate(protocol, root)
    builder = load_module(root / "build_probe_queue.py", "anarres_formal_queue_builder")
    panel_path = root / protocol["source"]["development_panel"]
    expected = builder.build_queue(
        protocol,
        json.loads(panel_path.read_text(encoding="utf-8")),
        protocol_sha256=hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        panel_sha256=hashlib.sha256(panel_path.read_bytes()).hexdigest(),
    )
    if queue != expected:
        raise FormalCliError("the repeated-measurement queue does not match its protocol")
    authorization_path = root / REPEATED_MEASUREMENT_AUTHORIZATION
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    # Execution needs a separate authorization record that binds this protocol and queue.
    authorized = (
        authorization.get("authorized") is True
        and authorization.get("protocol_sha256") == digest(protocol_path).removeprefix("sha256:")
        and authorization.get("queue_sha256") == digest(queue_path).removeprefix("sha256:")
    )
    release_path = root / REPEATED_MEASUREMENT_RELEASE / "measurement.json"
    measurement = None
    if release_path.is_file():
        measurement = json.loads(release_path.read_text(encoding="utf-8"))
        bound = {
            "protocol_sha256": protocol_path,
            "queue_sha256": queue_path,
            "authorization_sha256": authorization_path,
            "analysis_sha256": root / protocol["measurement"]["analysis_contract"],
        }
        for field, path in bound.items():
            if measurement["inputs"][field] != digest(path).removeprefix("sha256:"):
                raise FormalCliError(f"the released repeated measurement names another {field}")
    return {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": digest(protocol_path),
        "queue_id": queue["queue_id"],
        "queue_sha256": digest(queue_path),
        "queued_attempts": len(queue["attempts"]),
        "frozen": True,
        "execution_authorized": authorized,
        "authorization_sha256": digest(authorization_path),
        "released": measurement is not None,
        "measurement": None if measurement is None else released_summary(measurement, release_path),
    }


def released_summary(measurement: dict[str, Any], path: Path) -> dict[str, Any]:
    """Summarize the released aggregate without recomputing it."""

    summary: dict[str, Any] = {
        "measurement_sha256": digest(path),
        "decision": measurement["decision"],
        "abstention_reason": measurement["abstention_reason"],
    }
    if measurement["decision"] != "ready":
        return summary
    support = measurement["support"]
    return {
        **summary,
        "attempt_outcomes": measurement["attempt_outcomes"],
        "strict_successes": support["pooled_strict_successes"],
        "strict_trials": support["pooled_strict_trials"],
        "mixed_specification_groups": support["mixed_specification_groups"],
        "readiness_gate_passed": measurement["readiness"]["passes_readiness_gate"],
        "mode_measurements": {
            mode: {
                "usable_signal_density": values["coordinates"]["rho_per_million_model_tokens"],
                "effective_verification_coverage": values["coordinates"]["effective_coverage_H"],
                "mixed_specification_groups": values["coordinates"]["mixed_specification_groups"],
                "model_tokens": values["coordinates"]["model_tokens"],
            }
            for mode, values in sorted(measurement["measurements_by_mode"].items())
        },
        "planning_usd": measurement["cost"]["planning_usd"],
    }


def verify_release_manifest(release: Path) -> None:
    """Require every released file, and only those files, to match its listed digest."""

    manifest = release / "MANIFEST.sha256"
    listed = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        value, separator, name = line.partition("  ")
        if not separator or len(value) != 64:
            raise FormalCliError(f"the release manifest line {number} is malformed")
        listed[name.removeprefix("./")] = value
    present = {
        path.relative_to(release).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in release.rglob("*")
        if path.is_file() and path != manifest
    }
    if present != listed:
        changed = sorted(set(present.items()) ^ set(listed.items()))
        raise FormalCliError(f"the released records disagree with their manifest: {changed[0][0]}")


def run_aggregator(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, cwd=root, timeout=600)
    except subprocess.TimeoutExpired as error:
        raise FormalCliError("the frozen aggregator did not finish within 600 seconds") from error


def reproduce_repeated_measurement(repository: Path) -> str:
    """Rerun the frozen aggregator over the released run records and require identical bytes."""

    root = study_root(repository)
    release = root / REPEATED_MEASUREMENT_RELEASE
    # The aggregator reads only some run-record fields, so the manifest covers every byte.
    verify_release_manifest(release)
    with tempfile.TemporaryDirectory(prefix="anarres-formal-measurement-") as directory:
        output = Path(directory) / "measurement.json"
        completed = run_aggregator(
            [
                sys.executable,
                str(root / "aggregate_codex_sol_measurements.py"),
                "--protocol",
                str(root / "policy-probe-protocol.codex-sol-v2.json"),
                "--queue",
                str(root / "probe-queue.codex-sol-v2.json"),
                "--authorization",
                str(root / REPEATED_MEASUREMENT_AUTHORIZATION),
                "--grades",
                str(release / "grades"),
                "--output",
                str(output),
            ],
            root,
        )
        if completed.returncode != 0:
            reason = (completed.stderr.strip().splitlines() or ["no error output"])[-1]
            raise FormalCliError(f"the frozen aggregator rejected the released records: {reason}")
        if output.read_bytes() != (release / "measurement.json").read_bytes():
            raise FormalCliError("the released repeated measurement does not reproduce")
    return digest(release / "measurement.json")


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
    boundary_qualified = task_boundary_status(repository)["qualified"]
    repeated = repeated_measurement_status(repository)
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
        "runtime_qualification_available": True,
        "runtime_qualified": False,
        "task_only_boundary_qualified": boundary_qualified,
        "repeated_measurement": repeated,
        "policy_probe_available": False,
        "next_required_gate": next_gate(boundary_qualified, repeated),
    }


def next_gate(boundary_qualified: bool, repeated: dict[str, Any]) -> str:
    if not boundary_qualified:
        return "task-only containment requalification before repeated measurement"
    if not repeated["execution_authorized"]:
        return "execution authorization for the frozen repeated measurement"
    if not repeated["released"]:
        return "release of the authorized repeated measurement"
    if repeated["measurement"]["decision"] != "ready":
        return "a policy or task change after the repeated-measurement abstention"
    # GPT-5.6 Sol runs through a hosted API, and the comparison needs a policy we can train.
    return "a trainable starting policy and a frozen prospective candidate panel"


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
    boundary = task_boundary_status(repository)
    repeated = repeated_measurement_status(repository)
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
            "task_only_boundary_passed": boundary["qualified"],
            "followup_required": not boundary["qualified"],
        },
        "task_only_boundary": boundary,
        "repeated_measurement": repeated,
        "decision": {
            "repeated_measurement_authorized": repeated["execution_authorized"],
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
    repeated = repeated_measurement_status(repository)
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
        "repeated_measurement_authorized": repeated["execution_authorized"],
        "repeated_measurement_digest": (
            reproduce_repeated_measurement(repository) if repeated["released"] else None
        ),
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

    qualify_runtime = commands.add_parser(
        "qualify-runtime",
        help="Validate a source-bound Vero runtime without contacting a model.",
    )
    qualify_runtime.add_argument("--manifest", type=Path, required=True)
    qualify_runtime.add_argument("--runtime", type=Path, required=True)
    qualify_runtime.add_argument("--lean-executable", type=Path, required=True)
    qualify_runtime.add_argument("--lake-executable", type=Path, required=True)
    qualify_runtime.add_argument("--output", type=Path)
    qualify_runtime.add_argument("--force", action="store_true")
    qualify_runtime.add_argument("--json", action="store_true")
    qualify_runtime.set_defaults(handler=command_qualify_runtime)

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
    if value.get("qualification_state") == "source_qualified_runtime_pending":
        print("Formal verification source")
        print(f"  ✓ Qualified    {value['environment_id']}")
        print(f"    Revision           {value['source_revision']}")
        print(f"    License            {value['source_license']}")
        print("    Runtime            pending")
        print()
        print("Inventory")
        print(f"    Benchmarks         {value['benchmarks']}")
        print(f"    Modules            {value['modules']}")
        print(f"    APIs               {value['apis']}")
        print(f"    Specifications     {value['specifications']}")
        languages = ", ".join(
            f"{language} {count}" for language, count in value["source_languages"].items()
        )
        print(f"    Languages          {languages}")
        print(f"    Lean               {value['lean_version']}")
        print(f"    Modes              {', '.join(value['modes'])}")
        print(f"    Verified artifacts {value['verified_core_artifacts']}")
        print()
        print("Next  anarres formal qualify-runtime --help")
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
