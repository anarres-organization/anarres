"""Task-oriented CLI for released agentic-coding environment studies."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from anarres.core import consume_adapter_invocation

from .marin import MarinEvidenceError, audit_fixed_validation


class CodingCliError(ValueError):
    """Raised when released coding evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "coding",
        "version": "0.1.0",
        "protocol_version": 2,
        "domain": "agentic-terminal-coding",
        "executable": "anarres-coding",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "audit-marin-evidence",
            "profile",
            "regression-report",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "agentic-coding-policy-aligned-progression-v1",
            "rlve-prospective-mixture-probe-v1",
            "tmax-common-reference-bridge-v1",
        ],
        "source_formats": [],
    }


def repository_root(explicit: Path | None) -> Path:
    """Resolve a checkout containing the released coding study."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / "experiments/agentic/coding-environment-selection/README.md").is_file():
                return candidate
    raise CodingCliError(
        "Anarres repository not found. Run inside the repository or pass --repository."
    )


def study_root(repository: Path) -> Path:
    return repository / "experiments/agentic/coding-environment-selection"


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CodingCliError(f"required coding record is missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CodingCliError(f"expected a JSON object in {path}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise CodingCliError(f"cannot load released coding exporter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    study = study_root(repository_root(args.repository))
    exact = read_object(study / "results/summary.json")
    bridge = read_object(study / "results/retrospective-bridge-summary.json")
    regression = read_object(study / "results/task-regression-summary.json")
    return {
        "domain": "agentic-terminal-coding",
        "evidence_stage": "prospective_source_panel_plus_retrospective_cross_source_bridge",
        "independent_exact_decisions": exact["independent_training_decisions"],
        "exact_best_candidate_decisions": exact["aggregate"]["policy_response_rule"][
            "best_endpoint_decisions"
        ],
        "exact_reported_endpoints": exact["nested_reported_endpoints"],
        "exact_mean_regret_points": exact["aggregate"]["policy_response_rule"]["mean_regret_pp"],
        "bridge_sources": bridge["sources"],
        "bridge_independent_training_decisions": bridge["independent_training_decisions"],
        "bridge_pairwise_ordering": bridge["practical_measurement_rule"]["pairwise_ordering"],
        "bridge_mean_normalized_regret": bridge["practical_measurement_rule"][
            "mean_normalized_regret"
        ],
        "regression_held_out_repositories": regression["held_out_repositories"],
        "regression_auc": regression["combined_auc"],
        "regression_top_20pct_recall": regression["top_20pct_recall"],
        "native_policy_probe_available": False,
        "marin_evidence_audit_available": True,
        "allocation_boundary": (
            "Candidate profiles can be compared only under a shared starting policy, training "
            "contract, budget, and held-out target."
        ),
    }


def command_regressions(args: argparse.Namespace) -> dict[str, Any]:
    study = study_root(repository_root(args.repository))
    return read_object(study / "results/task-regression-summary.json")


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    study = study_root(repository_root(args.repository))
    exporters = []
    if args.panel in {"released", "all"}:
        exporters.append(
            (
                "released",
                study / "scripts/export_environment_profiles.py",
                args.output / "released",
            )
        )
    if args.panel in {"external", "all"}:
        exporters.append(
            (
                "external",
                study / "scripts/export_external_profiles.py",
                args.output / "external",
            )
        )
    reports = {}
    for name, path, output in exporters:
        module = load_module(path, f"anarres_coding_{name}_exporter")
        paths = module.export(output)
        reports[name] = {"output": str(output), "profiles": len(paths)}
    return {"status": "exported", "panels": reports}


def command_audit_marin(args: argparse.Namespace) -> dict[str, Any]:
    return audit_fixed_validation(
        args.csv,
        expected_sha256=args.sha256,
        source_revision=args.source_revision,
        source_license=args.source_license,
    )


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    study = study_root(repository)
    scripts = sorted((study / "scripts").glob("reproduce*.py"))
    checked = []
    for script in scripts:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=repository,
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode != 0:
            raise CodingCliError(f"reproducer failed for {script.name}: {completed.stderr.strip()}")
        checked.append(script.name)
    manifest = study / "MANIFEST.sha256"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        path = repository / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise CodingCliError(f"manifest digest mismatch for {relative}")
    return {
        "status": "verified",
        "reproducers": checked,
        "manifest_entries": len(manifest.read_text(encoding="utf-8").splitlines()),
    }


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<38} {rendered}")


def add_repository(command: argparse.ArgumentParser) -> None:
    command.add_argument("--repository", type=Path)
    command.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres coding",
        description="Inspect and verify released agentic-coding environment evidence.",
    )
    commands = result.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="Show released coding evidence and boundaries.")
    add_repository(status)
    status.set_defaults(handler=command_status)

    regressions = commands.add_parser(
        "regressions", help="Report the released task-level regression-risk audit."
    )
    add_repository(regressions)
    regressions.set_defaults(handler=command_regressions)

    profile = commands.add_parser(
        "profile", help="Export released outcome-free candidate measurements."
    )
    add_repository(profile)
    profile.add_argument("--output", type=Path, required=True)
    profile.add_argument("--panel", choices=("released", "external", "all"), default="all")
    profile.set_defaults(handler=command_profile)

    marin = commands.add_parser(
        "audit-marin-evidence",
        help="Validate Marin fixed-validation evidence without merging unlike targets.",
    )
    marin.add_argument("--csv", type=Path, required=True)
    marin.add_argument("--sha256", required=True)
    marin.add_argument("--source-revision", required=True)
    marin.add_argument("--source-license", required=True)
    marin.add_argument("--json", action="store_true")
    marin.set_defaults(handler=command_audit_marin)

    verify = commands.add_parser("verify", help="Reproduce and verify released coding evidence.")
    add_repository(verify)
    verify.set_defaults(handler=command_verify)
    return result


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="coding")
        arguments = parser().parse_args(raw_arguments)
        print_result(arguments.handler(arguments), arguments.json)
    except (
        CodingCliError,
        MarinEvidenceError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
