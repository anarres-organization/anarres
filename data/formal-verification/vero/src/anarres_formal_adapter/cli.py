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


class FormalCliError(ValueError):
    """Raised when released Vero evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "formal",
        "version": "0.1.0",
        "protocol_version": 1,
        "domain": "formal-verification",
        "executable": "anarres-formal",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": ["profile", "status", "verify"],
        "measurement_contracts": [
            "vero-leanstral-development-probe-v5:codeproof",
            "vero-leanstral-development-probe-v5:proof",
        ],
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


def native_paths(repository: Path) -> dict[str, Path]:
    root = study_root(repository)
    return {
        "result": root / "results/development-policy-measurement.v1.json",
        "protocol": root / "policy-probe-protocol.v5.json",
        "source": root / "source-pin.json",
    }


def validate_native(repository: Path) -> tuple[ModuleType, dict[str, Any]]:
    native = load_native_adapter(repository)
    paths = native_paths(repository)
    result = native.read_object(paths["result"])
    protocol = native.read_object(paths["protocol"])
    source = native.read_object(paths["source"])
    native.validate_inputs(result, protocol, source, paths["protocol"])
    return native, {"result": result, "protocol": protocol, "source": source}


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    _, records = validate_native(repository)
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


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
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

    status = commands.add_parser("status", help="Show support and authorization status.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export the native Vero profile inputs.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

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
    except (FormalCliError, ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
