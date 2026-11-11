"""CLI for the released Q07820 reaction-bank measurements."""

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

from .source import SOURCE_FORMAT, MolecularSourceError, bundle_digest, qualify_bundle


class MolecularCliError(ValueError):
    """Raised when released molecular evidence cannot support a command."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "molecular",
        "version": "0.3.0",
        "protocol_version": 2,
        "domain": "molecular-design",
        "executable": "anarres-molecular",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": ["profile", "source-digest", "source-qualification", "status", "verify"],
        "measurement_contracts": ["rxnflow-q07820-bank-v4"],
        "source_formats": [SOURCE_FORMAT],
    }


def repository_root(explicit: Path | None = None) -> Path:
    """Resolve a checkout containing the released reaction-bank study."""

    starts = [explicit.resolve()] if explicit is not None else [Path.cwd().resolve()]
    relative = Path(
        "experiments/ai-for-science/molecular-design/"
        "reaction-environment-selection/scripts/export_environment_profiles.py"
    )
    for start in starts:
        for candidate in (start, *start.parents):
            if (candidate / relative).is_file():
                return candidate
    raise MolecularCliError(
        "Anarres repository not found. Pass --repository with the released checkout."
    )


def study_root(repository: Path) -> Path:
    return repository / "experiments/ai-for-science/molecular-design/reaction-environment-selection"


def load_exporter(repository: Path) -> ModuleType:
    path = study_root(repository) / "scripts/export_environment_profiles.py"
    specification = importlib.util.spec_from_file_location(
        "anarres_molecular_reaction_bank_exporter", path
    )
    if specification is None or specification.loader is None:
        raise MolecularCliError(f"cannot load the released molecular adapter: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def export_profiles(repository: Path, output_dir: Path, force: bool = False) -> list[Path]:
    """Run the authoritative exporter without reproducing its calculations."""

    exporter = load_exporter(repository)
    return exporter.export_profiles(output_dir=output_dir, force=force)


def read_profile(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MolecularCliError(f"expected a profile object in {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    with tempfile.TemporaryDirectory(prefix="anarres-molecular-status-") as directory:
        outputs = export_profiles(repository, Path(directory))
        profile = read_profile(outputs[0])
    attributes = profile["attributes"]
    checks = {check["check_id"]: check for check in profile["qualification_checks"]}
    confirmation_passed = checks["bank-confirmation"]["status"] == "pass"
    return {
        "study": "prospective-reaction-environment-selection",
        "domain": profile["domain"],
        "target_id": attributes["target_id"],
        "bank_count": len(outputs),
        "bank_confirmation_passed": confirmation_passed,
        "confirmation_rule": attributes["confirmation_rule"],
        "failed_confirmation_checks": [
            item for item in attributes["failed_confirmation_checks"].split(",") if item
        ],
        "profiles_ready": confirmation_passed,
        "development_training_authorized": confirmation_passed,
        "training_outcomes_opened": attributes["training_outcomes_opened"],
    }


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    outputs = export_profiles(repository, args.output_dir, force=args.force)
    profile = read_profile(outputs[0])
    checks = {check["check_id"]: check for check in profile["qualification_checks"]}
    confirmation_passed = checks["bank-confirmation"]["status"] == "pass"
    return {
        "status": "exported",
        "profile_count": len(outputs),
        "profiles_ready": confirmation_passed,
        "development_training_authorized": confirmation_passed,
        "training_outcomes_opened": False,
        "outputs": [str(path) for path in outputs],
    }


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    with tempfile.TemporaryDirectory(prefix="anarres-molecular-verify-") as directory:
        root = Path(directory)
        first = export_profiles(repository, root / "first")
        second = export_profiles(repository, root / "second")
        deterministic = [path.read_bytes() for path in first] == [
            path.read_bytes() for path in second
        ]
        digests = {path.name: f"sha256:{sha256(path)}" for path in first}
        profile = read_profile(first[0])
    checks = {check["check_id"]: check for check in profile["qualification_checks"]}
    confirmation_passed = checks["bank-confirmation"]["status"] == "pass"
    if not deterministic:
        raise MolecularCliError("profile export is not deterministic")
    return {
        "status": "pass",
        "profile_count": len(digests),
        "profile_digests": digests,
        "deterministic": deterministic,
        "bank_confirmation_passed": confirmation_passed,
        "development_training_authorized": confirmation_passed,
        "training_outcomes_opened": False,
    }


def command_source_digest(args: argparse.Namespace) -> dict[str, Any]:
    """Compute the revision used to initialize one native bank bundle."""

    digest = bundle_digest(args.source.resolve())
    return {
        "native_format": SOURCE_FORMAT,
        "source": str(args.source.resolve()),
        "revision": f"sha256:{digest}",
    }


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Qualify one native Q07820 bank bundle without opening outcomes."""

    descriptor = adapter_descriptor()
    source = load_source_manifest(
        args.manifest,
        expected_adapter="molecular",
        expected_version=descriptor["version"],
        expected_domain=descriptor["domain"],
        accepted_formats=tuple(descriptor["source_formats"]),
    )
    observed_revision = f"sha256:{bundle_digest(source.source)}"
    if source.revision != observed_revision:
        raise MolecularCliError(
            "manifest source revision does not match the molecular bundle; "
            f"observed {observed_revision}"
        )
    report = qualify_bundle(source.source)
    return {
        "status": "qualified",
        "environment_id": source.environment_id,
        "native_format": source.native_format,
        "source_revision": source.revision,
        "source_license": source.license,
        **report,
        "policy_probe_available": False,
        "training_started": False,
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres molecular",
        description="Inspect and export released Q07820 reaction-bank measurements.",
    )
    commands = result.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Show qualification and sealing status.")
    add_common(status)
    status.set_defaults(handler=command_status)

    profile = commands.add_parser("profile", help="Export native reaction-bank profiles.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    source_digest = commands.add_parser(
        "source-digest", help="Compute the revision of a native Q07820 bank bundle."
    )
    source_digest.add_argument("--source", type=Path, required=True)
    source_digest.add_argument("--json", action="store_true")
    source_digest.set_defaults(handler=command_source_digest)

    qualify_source = commands.add_parser(
        "qualify-source", help="Validate a native Q07820 bank bundle."
    )
    qualify_source.add_argument("--manifest", type=Path, required=True)
    qualify_source.add_argument("--json", action="store_true")
    qualify_source.set_defaults(handler=command_qualify_source)

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
        print(f"{label:<36} {rendered}")


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="molecular")
        arguments = parser().parse_args(raw_arguments)
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except FileExistsError as error:
        path = error.filename or (error.args[0] if error.args else "output")
        print(f"error: output already exists: {path}", file=sys.stderr)
        raise SystemExit(1) from error
    except (
        MolecularCliError,
        MolecularSourceError,
        ValueError,
        OSError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
