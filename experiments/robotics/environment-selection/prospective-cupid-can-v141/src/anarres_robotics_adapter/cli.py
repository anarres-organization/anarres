"""Task-oriented CLI for the released CUPID Can v1.4.1 measurements."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


class RoboticsCliError(ValueError):
    """Raised when a released robotics workflow cannot be verified."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "robotics",
        "version": "0.1.0",
        "protocol_version": 1,
        "domain": "robotics",
        "executable": "anarres-robotics",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": ["profile", "status", "verify"],
        "measurement_contracts": [
            "robotics.cupid-can-v141-candidate-measurement.v1",
        ],
    }


def repository_root(explicit: Path | None = None) -> Path:
    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    starts.append(Path(__file__).resolve())
    relative = Path(
        "experiments/robotics/environment-selection/"
        "prospective-cupid-can-v141/export_environment_profiles.py"
    )
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / relative).is_file():
                return candidate
    raise RoboticsCliError(
        "Anarres repository not found. Pass --repository with a released checkout."
    )


def study_root(repository: Path) -> Path:
    return repository / "experiments/robotics/environment-selection/prospective-cupid-can-v141"


def load_native_adapter(repository: Path) -> ModuleType:
    path = study_root(repository) / "export_environment_profiles.py"
    specification = importlib.util.spec_from_file_location(
        "anarres_robotics_cupid_native_adapter", path
    )
    if specification is None or specification.loader is None:
        raise RoboticsCliError(f"cannot load native robotics adapter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def native_paths(repository: Path) -> dict[str, Path]:
    root = study_root(repository)
    return {
        "measurements": root / "PROFILE_MEASUREMENTS.json",
        "protocol": root / "PROTOCOL.json",
        "sources": root / "SOURCES.json",
        "qualification": root / "QUALIFICATION.json",
    }


def validate_native(repository: Path) -> tuple[ModuleType, dict[str, Any]]:
    native = load_native_adapter(repository)
    paths = native_paths(repository)
    measurements = native.read_object(paths["measurements"])
    protocol = native.read_object(paths["protocol"])
    sources = native.read_object(paths["sources"])
    qualification = native.read_object(paths["qualification"])
    native.validate_inputs(
        measurements,
        protocol,
        sources,
        qualification,
        paths["protocol"],
        paths["qualification"],
    )
    return native, {
        "measurements": measurements,
        "protocol": protocol,
        "qualification": qualification,
    }


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    _, records = validate_native(repository)
    measurements = records["measurements"]
    qualification = records["qualification"]
    return {
        "study_id": measurements["study_id"],
        "domain": "robotics",
        "source_contract": "RoboMimic Can v1.4.1",
        "candidate_count": len(measurements["candidates"]),
        "qualification_passed": qualification.get("passed") is True,
        "measurement_reliability_passed": (
            measurements["measurement"]["reliability_gate_passed"] is True
        ),
        "candidate_outcomes_opened": measurements["outcomes_read"],
        "profile_ready": (
            qualification.get("passed") is True
            and measurements["measurement"]["reliability_gate_passed"] is True
            and measurements["outcomes_read"] is False
        ),
    }


def export_profiles(repository: Path, output_dir: Path, force: bool = False) -> list[Path]:
    native, _ = validate_native(repository)
    paths = native_paths(repository)
    return native.export_profiles(
        measurements_path=paths["measurements"],
        protocol_path=paths["protocol"],
        sources_path=paths["sources"],
        qualification_path=paths["qualification"],
        output_dir=output_dir,
        force=force,
    )


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    outputs = export_profiles(repository, args.output_dir, force=args.force)
    return {
        "status": "exported",
        "profile_count": len(outputs),
        "candidate_outcomes_opened": False,
        "outputs": [str(path) for path in outputs],
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    with tempfile.TemporaryDirectory(prefix="anarres-robotics-verify-") as directory:
        outputs = export_profiles(repository, Path(directory))
        sizes = [path.stat().st_size for path in outputs]
    return {
        "status": "pass",
        "profile_count": len(outputs),
        "nonempty_profiles": all(size > 0 for size in sizes),
        "candidate_outcomes_opened": False,
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres robotics",
        description="Inspect and export the released CUPID Can v1.4.1 measurements.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show measurement and sealing status.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export native candidate profile inputs.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    verify = commands.add_parser("verify", help="Validate records and deterministic export.")
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
    except (RoboticsCliError, ValueError, OSError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
