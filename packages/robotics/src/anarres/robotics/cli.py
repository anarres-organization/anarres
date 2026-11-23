"""Command-line entry point for the study-independent robotics adapter."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import import_module
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from anarres.core import EnvironmentSource, consume_adapter_invocation, load_source_manifest

from .contract import RoboticsContractError
from .drivers.base import installed_formats, load_driver
from .runners import protocol

ADAPTER_VERSION = "0.6.0"
ADAPTER_COMMANDS = ("probe-source", "qualify-source")
STUDY_COMMAND_GROUP = "anarres.robotics.study_commands"
MEASUREMENT_CONTRACT_GROUP = "anarres.robotics.measurement_contracts"


def study_commands() -> dict[str, str]:
    """Map installed study command names to their handlers without importing them."""

    commands: dict[str, str] = {}
    for entry in entry_points(group=STUDY_COMMAND_GROUP):
        if entry.name in ADAPTER_COMMANDS:
            raise RoboticsContractError(f"study command {entry.name} shadows an adapter command")
        if commands.setdefault(entry.name, entry.value) != entry.value:
            raise RoboticsContractError(f"two studies register the command {entry.name}")
    return commands


def run_study_command(target: str, arguments: list[str]) -> None:
    module_name, _, attribute = target.partition(":")
    getattr(import_module(module_name), attribute)(arguments)


def adapter_descriptor() -> dict[str, Any]:
    """Describe the installed adapter without importing drivers or opening sources.

    `policy-probe` stays undeclared until a real native source and runner pass
    conformance tests, as RFC 0006 requires. `probe-source` remains available
    through direct adapter invocation in the meantime.
    """

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "robotics",
        "version": ADAPTER_VERSION,
        "protocol_version": 2,
        "domain": "robotics",
        "executable": "anarres-robotics",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": sorted({"source-qualification", *study_commands()}),
        "measurement_contracts": sorted(
            {entry.name for entry in entry_points(group=MEASUREMENT_CONTRACT_GROUP)}
        ),
        "source_formats": installed_formats(),
    }


def load_source(manifest: Path) -> EnvironmentSource:
    descriptor = adapter_descriptor()
    return load_source_manifest(
        manifest,
        expected_adapter=descriptor["name"],
        expected_version=descriptor["version"],
        expected_domain=descriptor["domain"],
        accepted_formats=tuple(descriptor["source_formats"]),
    )


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Validate a native source through its driver without running a policy."""

    source = load_source(args.manifest)
    driver = load_driver(source.native_format)
    description = driver.describe(source)
    return {
        "status": "qualified",
        "description": description.to_record(),
        "probe_tasks": len(driver.tasks(source)),
        "policy_probe_available": False,
        "training_started": False,
        "candidate_outcomes_opened": False,
    }


def resolve_runner(executable: str, arguments: list[str]) -> list[str]:
    resolved = shutil.which(executable)
    if resolved is None:
        raise RoboticsContractError(f"policy runner executable not found: {executable}")
    return [resolved, *arguments]


def command_probe_source(args: argparse.Namespace) -> dict[str, Any]:
    """Plan a bounded probe, and launch the declared runner only with --execute."""

    if args.execute and args.runner is None:
        raise RoboticsContractError("--execute requires --runner")
    source = load_source(args.manifest)
    driver = load_driver(source.native_format)
    description = driver.describe(source)
    request = protocol.build_request(
        source,
        description,
        driver,
        policy=args.policy,
        policy_revision=args.policy_revision,
        limits={
            "max_steps": description.max_steps,
            "wall_clock_seconds": args.wall_clock_seconds,
        },
    )
    output = args.output.resolve()
    if output.exists() and not output.is_dir():
        raise RoboticsContractError("probe output must be a directory")
    planned = protocol.plan(request, output)
    if not args.execute:
        return planned
    runner = resolve_runner(args.runner, args.runner_arg)
    return {**planned, **protocol.execute(runner, output), "runner_launched": True}


def parser() -> argparse.ArgumentParser:
    studies = ", ".join(sorted(study_commands())) or "none installed"
    root = argparse.ArgumentParser(
        prog="anarres-robotics", description=__doc__, epilog=f"Study commands: {studies}"
    )
    commands = root.add_subparsers(dest="command", required=True)

    qualify_source = commands.add_parser(
        "qualify-source", help="Validate a native robotics source through its driver."
    )
    qualify_source.add_argument("--manifest", type=Path, required=True)
    qualify_source.add_argument("--json", action="store_true")
    qualify_source.set_defaults(handler=command_qualify_source)

    probe_source = commands.add_parser(
        "probe-source", help="Plan a starting-policy probe, or run it with --execute."
    )
    probe_source.add_argument("--manifest", type=Path, required=True)
    probe_source.add_argument("--policy", required=True)
    probe_source.add_argument("--policy-revision", required=True)
    probe_source.add_argument("--output", type=Path, required=True)
    probe_source.add_argument("--wall-clock-seconds", type=int, default=3600)
    probe_source.add_argument("--runner", help="Policy-runner executable on PATH or a path.")
    probe_source.add_argument(
        "--runner-arg", action="append", default=[], help="Argument passed to the runner."
    )
    probe_source.add_argument("--execute", action="store_true")
    probe_source.add_argument(
        "--force", action="store_true", help="Reuse an existing output directory."
    )
    probe_source.add_argument("--json", action="store_true")
    probe_source.set_defaults(handler=command_probe_source)
    return root


def print_result(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    for key, item in value.items():
        label = key.replace("_", " ").title()
        rendered = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        print(f"{label:<32} {rendered}")


def main() -> None:
    raw_arguments = sys.argv[1:]
    if raw_arguments == ["--anarres-adapter-descriptor"]:
        print(json.dumps(adapter_descriptor(), indent=2, sort_keys=True))
        return
    try:
        raw_arguments = consume_adapter_invocation(raw_arguments, expected_name="robotics")
        studies = study_commands()
        if raw_arguments and raw_arguments[0] in studies:
            run_study_command(studies[raw_arguments[0]], raw_arguments)
            return
        arguments = parser().parse_args(raw_arguments)
        output = arguments.handler(arguments)
        print_result(output, arguments.json)
    except (RoboticsContractError, ValueError, OSError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    if output.get("status") in {"runner_failed", "incomplete"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
