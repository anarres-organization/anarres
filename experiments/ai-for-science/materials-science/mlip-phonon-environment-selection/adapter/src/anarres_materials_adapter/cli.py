"""CLI wrapper for the released MLIP candidate-measurement adapter."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


class MaterialsCliError(ValueError):
    """Raised when the released materials adapter cannot run."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "materials",
        "version": "0.2.0",
        "protocol_version": 1,
        "domain": "materials-interatomic-potentials",
        "executable": "anarres-materials",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": ["profile", "status", "verify"],
        "measurement_contracts": [
            "materials.mlip-phonon-candidate-measurement.v2",
        ],
    }


def repository_root(explicit: Path | None = None) -> Path:
    """Resolve a checkout containing the released study."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    for start in starts:
        for candidate in (start, *start.parents):
            if exporter_path(candidate).is_file():
                return candidate
    raise MaterialsCliError(
        "Anarres repository not found. Run inside a checkout or pass --repository"
    )


def study_root(repository: Path) -> Path:
    return (
        repository
        / "experiments/ai-for-science/materials-science/mlip-phonon-environment-selection"
    )


def exporter_path(repository: Path) -> Path:
    return study_root(repository) / "export_environment_profiles.py"


def load_exporter(repository: Path) -> ModuleType:
    path = exporter_path(repository)
    if not path.is_file():
        raise MaterialsCliError(f"materials profile exporter is missing: {path}")
    specification = importlib.util.spec_from_file_location(
        "anarres_materials_mlip_profile_exporter", path
    )
    if specification is None or specification.loader is None:
        raise MaterialsCliError(f"cannot load materials profile exporter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    bank = exporter.read_object(exporter.DEFAULT_BANK)
    validation = exporter.read_object(exporter.DEFAULT_VALIDATION)
    candidates = bank.get("candidates")
    if not isinstance(candidates, list):
        raise MaterialsCliError("candidate panel has no candidate list")
    first_candidate = sorted(candidate["candidate_id"] for candidate in candidates)[0]
    with tempfile.TemporaryDirectory(prefix="anarres-materials-status-") as directory:
        output = exporter.export_profiles(
            output_dir=Path(directory), candidate_ids=[first_candidate]
        )[0]
        checks = {
            check["check_id"]: check
            for check in json.loads(output.read_text(encoding="utf-8"))["qualification_checks"]
        }
    return {
        "domain": "materials-interatomic-potentials",
        "candidate_panel_status": bank.get("status"),
        "candidate_count": len(candidates),
        "measurement_records": validation.get("records"),
        "measurements_complete": validation.get("status") == "complete",
        "candidate_outcomes_opened": checks["candidate-outcomes-sealed"]["status"] != "pass",
        "final_training_panel_frozen": checks["final-panel-frozen"]["status"] == "pass",
        "predictive_evidence_available": False,
    }


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    outputs = exporter.export_profiles(
        output_dir=args.output_dir,
        candidate_ids=args.candidate_id,
        force=args.force,
    )
    return {
        "status": "exported",
        "candidate_count": len(outputs),
        "outputs": [str(path) for path in outputs],
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    exporter = load_exporter(repository)
    bank = exporter.read_object(exporter.DEFAULT_BANK)
    validation = exporter.read_object(exporter.DEFAULT_VALIDATION)
    candidate_ids = sorted(candidate["candidate_id"] for candidate in bank["candidates"])
    with tempfile.TemporaryDirectory(prefix="anarres-materials-verify-") as directory:
        root = Path(directory)
        first = exporter.export_profiles(output_dir=root / "first", candidate_ids=candidate_ids)
        second = exporter.export_profiles(output_dir=root / "second", candidate_ids=candidate_ids)
        stable = [path.read_bytes() for path in first] == [path.read_bytes() for path in second]
        if not stable:
            raise MaterialsCliError("materials profile export is not deterministic")
        observed_ids = []
        for path in first:
            profile = json.loads(path.read_text(encoding="utf-8"))
            observed_ids.append(profile["environment_id"])
            checks = {check["check_id"]: check for check in profile["qualification_checks"]}
            if checks["measurements-complete"]["status"] != "pass":
                raise MaterialsCliError("full measurement status was not preserved")
            if checks["candidate-outcomes-sealed"]["status"] != "pass":
                raise MaterialsCliError("candidate outcome seal did not pass")
            if checks["final-panel-frozen"]["status"] != "pass":
                raise MaterialsCliError("final panel seal did not pass")
        if observed_ids != candidate_ids:
            raise MaterialsCliError("materials profile export omitted or reordered candidates")

    measurement_shards = validation.get("measurement_sha256")
    if not isinstance(measurement_shards, dict) or len(measurement_shards) != 8:
        raise MaterialsCliError("full measurement shard identities were not preserved")
    return {
        "status": "pass",
        "profiles_checked": len(candidate_ids),
        "deterministic": True,
        "measurement_records": validation["records"],
        "measurement_shards_pinned": len(measurement_shards),
        "candidate_outcomes_sealed": True,
        "final_training_panel_frozen": True,
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres materials",
        description="Inspect and export released MLIP candidate measurements.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show the released measurement boundary.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export MLIP environment profiles.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--candidate-id", action="append")
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    verify = commands.add_parser("verify", help="Verify the released profile adapter.")
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
        print(f"{label:<32} {rendered}")


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
    except (MaterialsCliError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
