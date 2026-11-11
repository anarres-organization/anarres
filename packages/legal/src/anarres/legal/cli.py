"""CLI for released Anarres legal-reasoning environment studies."""

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

from . import lab_execution, lab_intake


class LegalCliError(ValueError):
    """Raised when released legal evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "legal",
        "version": "0.4.0",
        "protocol_version": 2,
        "domain": "legal-procedural-reasoning",
        "executable": "anarres-legal",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "lab-execution-contract",
            "lab-run-audit",
            "lab-workflow-intake",
            "profile",
            "regression-report",
            "source-qualification",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "harvey-lab-workflow-intake-v1",
            "syllogym-stage-a-policy-response-v1",
        ],
        "source_formats": ["harvey-lab-checkout-v1"],
    }


def repository_root(explicit: Path | None) -> Path:
    """Resolve an explicit checkout or a checkout containing the current directory."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "experiments/legal/environment-selection/README.md").is_file():
                return candidate
    raise LegalCliError(
        "Anarres repository not found. Pass --repository with a checkout containing "
        "the released legal records."
    )


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LegalCliError(f"required legal record is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LegalCliError(f"expected a JSON object in {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_exporter(repository: Path) -> ModuleType:
    path = (
        repository
        / "experiments/legal/environment-selection/scripts/export_environment_profiles.py"
    )
    specification = importlib.util.spec_from_file_location("anarres_legal_syllogym_exporter", path)
    if specification is None or specification.loader is None:
        raise LegalCliError(f"cannot load the released SylloGym exporter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_lab_reproducer(repository: Path) -> ModuleType:
    path = repository / "experiments/legal/lab-learning-dynamics/scripts/reproduce.py"
    specification = importlib.util.spec_from_file_location("anarres_legal_lab_reproducer", path)
    if specification is None or specification.loader is None:
        raise LegalCliError(f"cannot load the released LAB reproducer: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def load_lab_run_audit(repository: Path) -> ModuleType:
    path = repository / "experiments/legal/lab-workflow-intake/scripts/audit_runs.py"
    specification = importlib.util.spec_from_file_location("anarres_legal_lab_run_audit", path)
    if specification is None or specification.loader is None:
        raise LegalCliError(f"cannot load the LAB run audit: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def evidence_paths(repository: Path) -> dict[str, Path]:
    study = repository / "experiments/legal/environment-selection"
    return {
        "release_path": study / "data/measurement-release.json",
        "measurements_path": study / "data/pretraining-task-measurements.json",
        "selector_path": study / "data/selector-freeze.json",
        "decision_path": study / "data/frozen-decision.json",
        "sources_path": study / "SOURCES.json",
    }


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    legal = repository / "experiments/legal"
    release = read_object(legal / "environment-selection/data/measurement-release.json")
    decision = read_object(legal / "environment-selection/data/frozen-decision.json")
    lab = read_object(legal / "lab-learning-dynamics/results/summary.json")
    return {
        "domain": "legal-reasoning",
        "syllogym": {
            "measurement_status": release["status"],
            "candidate_ids": release["candidate_ids"],
            "candidate_training_outcomes_used_by_adapter": release["outcome_boundary"][
                "candidate_training_outcomes_used"
            ],
            "decision_artifact": decision["artifact"],
        },
        "lab": {
            "role": "separate_task_regression_evaluation",
            "profile_input": False,
            "result_record_available": True,
            "checkpoint_count": lab["checkpoint_count"],
            "workflow_intake_available": True,
            "workflow_intake_reads_outcomes": False,
            "execution_contract_available": True,
            "execution_contract_starts_execution": False,
            "native_source_format": "harvey-lab-checkout-v1",
            "native_source_qualification_available": True,
            "policy_probe_available": False,
            "run_audit_available": True,
        },
    }


def export_profiles(repository: Path, output_dir: Path, force: bool) -> list[Path]:
    exporter = load_exporter(repository)
    return exporter.export_profiles(
        **evidence_paths(repository),
        output_dir=output_dir,
        force=force,
    )


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    outputs = export_profiles(repository, args.output_dir, args.force)
    return {
        "status": "exported",
        "profile_count": len(outputs),
        "outputs": [str(path) for path in outputs],
        "outcomes_artifact_read": False,
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    with tempfile.TemporaryDirectory(prefix="anarres-legal-verify-") as directory:
        outputs = export_profiles(repository, Path(directory), False)
        digests = {path.name: f"sha256:{sha256(path)}" for path in outputs}
    return {
        "status": "pass",
        "profile_count": len(digests),
        "profile_digests": digests,
        "outcomes_artifact_read": False,
    }


def command_regressions(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    study = repository / "experiments/legal/lab-learning-dynamics"
    summary_path = study / "results/summary.json"
    risk_path = study / "data/regression-risk.json"
    checkpoints_path = study / "data/checkpoints.json"
    sources_path = study / "SOURCES.json"

    expected = read_object(summary_path)
    reproduced = load_lab_reproducer(repository).compute()
    if reproduced != expected:
        raise LegalCliError("recomputed LAB summary does not match the released result")

    risk = read_object(risk_path)
    return {
        "schema_version": "anarres.legal-regression-report.v1",
        "status": "released_reproduced",
        "study": "lab-learning-dynamics",
        "role": "separate_task_regression_evaluation",
        "profile_input": False,
        "feature_timing": risk["feature_timing"],
        "endpoint": risk["endpoint"],
        "validation": risk["validation"],
        "support": risk["support"],
        "metrics": risk["metrics"],
        "clustered_bootstrap": risk["clustered_bootstrap_combined_minus_behavior"],
        "learning_dynamics": expected,
        "claim_boundary": risk["claim_boundary"],
        "artifacts": {
            "checkpoints": f"sha256:{sha256(checkpoints_path)}",
            "regression_risk": f"sha256:{sha256(risk_path)}",
            "released_summary": f"sha256:{sha256(summary_path)}",
            "sources": f"sha256:{sha256(sources_path)}",
        },
    }


def command_lab_intake(args: argparse.Namespace) -> dict[str, Any]:
    summary, rows = lab_intake.build(args.lab_root.resolve(), args.source_revision)
    outputs = lab_intake.write(summary, rows, args.output_dir.resolve(), args.force)
    return {
        "status": summary["status"],
        "task_count": summary["support"]["tasks"],
        "practice_area_count": summary["support"]["practice_areas"],
        "profile_input": False,
        "outcomes_artifact_read": False,
        "model_responses_read": False,
        "outputs": [str(path) for path in outputs],
        "output_digests": {path.name: f"sha256:{sha256(path)}" for path in outputs},
        "claim_boundary": summary["claim_boundary"],
    }


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Validate one pinned LAB checkout without reading runs or outcomes."""

    descriptor = adapter_descriptor()
    source = load_source_manifest(
        args.manifest,
        expected_adapter="legal",
        expected_version=descriptor["version"],
        expected_domain=descriptor["domain"],
        accepted_formats=tuple(descriptor["source_formats"]),
    )
    if source.license != "MIT":
        raise LegalCliError(
            "Harvey LAB source license must be recorded as MIT for this source format"
        )
    summary, _ = lab_intake.build(source.source, source.revision)
    if summary["status"] != "qualified":
        missing = summary["support"]["tasks"] - summary["support"]["tasks_with_documents"]
        raise LegalCliError(f"LAB checkout has incomplete matter files for {missing} task(s)")
    return {
        "status": "qualified",
        "environment_id": source.environment_id,
        "native_format": source.native_format,
        "source_revision": source.revision,
        "source_license": source.license,
        "task_set_sha256": summary["source"]["task_set_sha256"],
        "tasks": summary["support"]["tasks"],
        "practice_areas": summary["support"]["practice_areas"],
        "rubric_criteria": summary["support"]["rubric_criteria"],
        "tasks_with_documents": summary["support"]["tasks_with_documents"],
        "policy_probe_available": False,
        "model_responses_read": False,
        "outcomes_read": False,
    }


def command_lab_runs(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    audit = load_lab_run_audit(repository)
    contract_path = getattr(args, "execution_contract", None)
    execution_contract = (
        lab_execution.load(contract_path.resolve()) if contract_path is not None else None
    )
    summary, rows = audit.build(args.results_root.resolve(), args.run_manifest, execution_contract)
    outputs = audit.write(summary, rows, args.output_dir.resolve(), args.force)
    return {
        "status": summary["status"],
        "support": summary["support"],
        "profile_input": False,
        "outputs": [str(path) for path in outputs],
        "output_digests": {path.name: f"sha256:{sha256(path)}" for path in outputs},
        "claim_boundary": summary["claim_boundary"],
    }


def command_lab_contract(args: argparse.Namespace) -> dict[str, Any]:
    contract = lab_execution.load(args.input.resolve())
    lab_execution.write(contract, args.output.resolve(), args.force)
    return {
        "status": "qualified",
        "schema_version": contract["schema_version"],
        "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"],
        "starting_policy_model": contract["starting_policy_stage"]["policy"]["model_id"],
        "judge_models": [judge["model_id"] for judge in contract["judge_stage"]["judges"]],
        "execution_started": False,
        "policy_probe_available": False,
        "output": str(args.output.resolve()),
    }


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<34} {rendered}")


def add_common(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--repository", type=Path)
    subparser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres legal",
        description="Inspect and export released Anarres legal-reasoning evidence.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show released legal evidence boundaries.")
    add_common(status)
    status.set_defaults(handler=command_status)

    qualify_source = commands.add_parser(
        "qualify-source", help="Validate a pinned Harvey LAB task checkout."
    )
    qualify_source.add_argument("--manifest", type=Path, required=True)
    qualify_source.add_argument("--json", action="store_true")
    qualify_source.set_defaults(handler=command_qualify_source)

    profile = commands.add_parser(
        "profile", help="Export outcome-blind SylloGym environment profiles."
    )
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    regressions = commands.add_parser(
        "regressions",
        help="Reproduce and report the separate LAB task-regression evaluation.",
    )
    add_common(regressions)
    regressions.set_defaults(handler=command_regressions)

    lab_intake = commands.add_parser(
        "lab-intake",
        help="Validate and inventory an outcome-blind Harvey LAB checkout.",
    )
    add_common(lab_intake)
    lab_intake.add_argument("--lab-root", type=Path, required=True)
    lab_intake.add_argument("--source-revision", required=True)
    lab_intake.add_argument("--output-dir", type=Path, required=True)
    lab_intake.add_argument("--force", action="store_true")
    lab_intake.set_defaults(handler=command_lab_intake)

    lab_runs = commands.add_parser(
        "lab-runs",
        help="Audit model-agnostic LAB run, judge, behavior, and cost records.",
    )
    add_common(lab_runs)
    lab_runs.add_argument("--results-root", type=Path, required=True)
    lab_runs.add_argument("--run-manifest", type=Path)
    lab_runs.add_argument("--execution-contract", type=Path)
    lab_runs.add_argument("--output-dir", type=Path, required=True)
    lab_runs.add_argument("--force", action="store_true")
    lab_runs.set_defaults(handler=command_lab_runs)

    lab_contract = commands.add_parser(
        "lab-contract",
        help="Validate and content-address a portable LAB execution contract.",
    )
    lab_contract.add_argument("--input", type=Path, required=True)
    lab_contract.add_argument("--output", type=Path, required=True)
    lab_contract.add_argument("--force", action="store_true")
    lab_contract.add_argument("--json", action="store_true")
    lab_contract.set_defaults(handler=command_lab_contract)

    verify = commands.add_parser(
        "verify", help="Verify and deterministically regenerate SylloGym profiles."
    )
    add_common(verify)
    verify.set_defaults(handler=command_verify)
    return result


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="legal")
        arguments = parser().parse_args(raw_arguments)
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except FileExistsError as error:
        path = error.filename or (error.args[0] if error.args else "output")
        print(f"error: output already exists: {path}", file=sys.stderr)
        raise SystemExit(1) from error
    except (LegalCliError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
