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


class LegalCliError(ValueError):
    """Raised when released legal evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "legal",
        "version": "0.2.0",
        "protocol_version": 1,
        "domain": "legal-procedural-reasoning",
        "executable": "anarres-legal",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": ["lab-workflow-intake", "profile", "regression-report", "status", "verify"],
        "measurement_contracts": [
            "harvey-lab-workflow-intake-v1",
            "syllogym-stage-a-policy-response-v1",
        ],
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


def load_lab_intake(repository: Path) -> ModuleType:
    path = repository / "experiments/legal/lab-workflow-intake/scripts/build.py"
    specification = importlib.util.spec_from_file_location("anarres_legal_lab_intake", path)
    if specification is None or specification.loader is None:
        raise LegalCliError(f"cannot load the LAB workflow intake: {path}")
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
    repository = repository_root(args.repository)
    intake = load_lab_intake(repository)
    summary, rows = intake.build(args.lab_root.resolve(), args.source_revision)
    outputs = intake.write(summary, rows, args.output_dir.resolve(), args.force)
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

    verify = commands.add_parser(
        "verify", help="Verify and deterministically regenerate SylloGym profiles."
    )
    add_common(verify)
    verify.set_defaults(handler=command_verify)
    return result


def main() -> None:
    if sys.argv[1:] == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    arguments = parser().parse_args()
    try:
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
