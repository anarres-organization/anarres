"""CLI for molecular source qualification and released Q07820 evidence."""

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

from .probe import MolecularProbeError, build_probe_plan, execute_probe_plan
from .source import SOURCE_FORMAT, MolecularSourceError, bundle_digest, qualify_source


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
        "capabilities": [
            "policy-probe",
            "profile",
            "source-digest",
            "source-qualification",
            "status",
            "verify",
        ],
        "measurement_contracts": [
            "q07820-starting-policy-endpoint-qualification-v2",
            "rxnflow-q07820-bank-v4",
        ],
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


def read_endpoint_qualification(repository: Path) -> dict[str, Any]:
    root = study_root(repository)
    result_path = root / "STARTING_POLICY_ENDPOINT_QUALIFICATION_RESULT_V2.json"
    contract_path = root / "STARTING_POLICY_ENDPOINT_QUALIFICATION_CONTRACT_V2.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("contract") != "q07820-starting-policy-endpoint-qualification-v2":
        raise MolecularCliError("starting-policy endpoint result uses the wrong contract")
    if result.get("attempts") != 4096:
        raise MolecularCliError("starting-policy endpoint result has the wrong attempt count")
    if result.get("inputs", {}).get("starting_policy_endpoint_contract_sha256") != sha256(
        contract_path
    ):
        raise MolecularCliError("starting-policy endpoint contract hash does not match")
    passed = (
        result.get("status") == "passed"
        and result.get("authorizes_matched_training") is True
        and all(result.get("checks", {}).values())
    )
    return {
        "passed": passed,
        "status": result.get("status"),
        "qualifying_attempts": result.get("qualifying_attempts"),
        "unique_qualifying_molecules": result.get("unique_qualifying_molecules"),
        "infrastructure_failures": result.get("infrastructure_failures"),
        "result_sha256": sha256(result_path),
    }


def read_matched_contract(repository: Path, endpoint_sha256: str) -> dict[str, Any]:
    root = study_root(repository)
    path = root / "MATCHED_TRAINING_EVALUATION_CONTRACT_V1.json"
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract") != "q07820-matched-training-evaluation-v1":
        raise MolecularCliError("matched training uses the wrong contract")
    endpoint_reference = contract.get("inputs", {}).get("starting_policy_endpoint_result", {})
    if endpoint_reference.get("sha256") != endpoint_sha256:
        raise MolecularCliError("matched training does not bind the released endpoint result")
    authorization = contract.get("authorization", {})
    frozen = (
        contract.get("status") == "frozen_after_endpoint_qualification_before_development_training"
        and authorization.get("development_training_authorized") is True
        and authorization.get("development_training_started") is False
        and authorization.get("development_or_prospective_outcomes_opened") is False
    )
    return {"frozen": frozen, "sha256": sha256(path)}


def command_status(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    with tempfile.TemporaryDirectory(prefix="anarres-molecular-status-") as directory:
        outputs = export_profiles(repository, Path(directory))
        profile = read_profile(outputs[0])
    attributes = profile["attributes"]
    checks = {check["check_id"]: check for check in profile["qualification_checks"]}
    confirmation_passed = checks["bank-confirmation"]["status"] == "pass"
    endpoint = read_endpoint_qualification(repository)
    matched = read_matched_contract(repository, endpoint["result_sha256"])
    return {
        "study": "prospective-reaction-environment-selection",
        "domain": profile["domain"],
        "target_id": attributes["target_id"],
        "bank_count": len(outputs),
        "bank_confirmation_passed": confirmation_passed,
        "endpoint_qualification_passed": endpoint["passed"],
        "endpoint_qualification_status": endpoint["status"],
        "endpoint_qualifying_attempts": endpoint["qualifying_attempts"],
        "endpoint_unique_qualifying_molecules": endpoint["unique_qualifying_molecules"],
        "endpoint_infrastructure_failures": endpoint["infrastructure_failures"],
        "endpoint_result_sha256": f"sha256:{endpoint['result_sha256']}",
        "matched_training_contract_frozen": matched["frozen"],
        "matched_training_contract_sha256": f"sha256:{matched['sha256']}",
        "confirmation_rule": attributes["confirmation_rule"],
        "failed_confirmation_checks": [
            item for item in attributes["failed_confirmation_checks"].split(",") if item
        ],
        "profiles_ready": confirmation_passed,
        "development_training_authorized": (
            confirmation_passed and endpoint["passed"] and matched["frozen"]
        ),
        "training_outcomes_opened": attributes["training_outcomes_opened"],
    }


def command_profile(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    outputs = export_profiles(repository, args.output_dir, force=args.force)
    profile = read_profile(outputs[0])
    checks = {check["check_id"]: check for check in profile["qualification_checks"]}
    confirmation_passed = checks["bank-confirmation"]["status"] == "pass"
    endpoint = read_endpoint_qualification(repository)
    matched = read_matched_contract(repository, endpoint["result_sha256"])
    return {
        "status": "exported",
        "profile_count": len(outputs),
        "profiles_ready": confirmation_passed,
        "endpoint_qualification_passed": endpoint["passed"],
        "matched_training_contract_frozen": matched["frozen"],
        "development_training_authorized": (
            confirmation_passed and endpoint["passed"] and matched["frozen"]
        ),
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
    endpoint = read_endpoint_qualification(repository)
    matched = read_matched_contract(repository, endpoint["result_sha256"])
    if not deterministic:
        raise MolecularCliError("profile export is not deterministic")
    return {
        "status": "pass",
        "profile_count": len(digests),
        "profile_digests": digests,
        "deterministic": deterministic,
        "bank_confirmation_passed": confirmation_passed,
        "endpoint_qualification_passed": endpoint["passed"],
        "endpoint_result_sha256": f"sha256:{endpoint['result_sha256']}",
        "matched_training_contract_frozen": matched["frozen"],
        "matched_training_contract_sha256": f"sha256:{matched['sha256']}",
        "development_training_authorized": (
            confirmation_passed and endpoint["passed"] and matched["frozen"]
        ),
        "training_outcomes_opened": False,
    }


def command_source_digest(args: argparse.Namespace) -> dict[str, Any]:
    """Compute the revision used to initialize one native environment."""

    digest = bundle_digest(args.source.resolve())
    return {
        "native_format": SOURCE_FORMAT,
        "source": str(args.source.resolve()),
        "revision": f"sha256:{digest}",
    }


def command_qualify_source(args: argparse.Namespace) -> dict[str, Any]:
    """Qualify one native molecular environment without opening outcomes."""

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
            "manifest source revision does not match the molecular source; "
            f"observed {observed_revision}"
        )
    report = qualify_source(source.source)
    return {
        "status": "qualified",
        "environment_id": source.environment_id,
        "native_format": source.native_format,
        "source_revision": source.revision,
        "source_license": source.license,
        **report,
        "policy_probe_available": True,
        "training_started": False,
    }


def command_probe_source(args: argparse.Namespace) -> dict[str, Any]:
    """Plan or explicitly execute the released endpoint producer."""

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
            "manifest source revision does not match the molecular source; "
            f"observed {observed_revision}"
        )
    output = args.output.resolve()
    if output.exists() and not output.is_dir():
        raise MolecularCliError("probe output must be a directory")
    output.mkdir(parents=True, exist_ok=True)
    repository = repository_root(args.repository)
    plan = build_probe_plan(
        source_root=source.source,
        repository=repository,
        policy_id=args.policy,
        policy_revision=args.policy_revision,
        output=output,
        sampler_python=args.sampler_python.resolve(),
        oracle_python=args.oracle_python.resolve(),
        device=args.device,
        docking_jobs=args.docking_jobs,
        metric_jobs=args.metric_jobs,
    )
    plan_path = output / "PROBE_PLAN.json"
    if plan_path.is_file():
        existing = json.loads(plan_path.read_text(encoding="utf-8"))
        if existing != plan:
            raise MolecularCliError("probe output contains a different immutable plan")
    else:
        temporary = plan_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(plan_path)
    if not args.execute:
        return {
            "status": "planned",
            "plan": str(plan_path),
            "plan_sha256": plan["plan_sha256"],
            "attempts": plan["attempts"],
            "evaluation_seed": plan["evaluation_seed"],
            "outcomes_opened": False,
        }
    result = execute_probe_plan(plan, output, force_incomplete=args.force)
    return {
        "status": result["status"],
        "plan": str(plan_path),
        "plan_sha256": plan["plan_sha256"],
        "run": str(output / "PROBE_RUN.json"),
        "result": result["result"],
    }


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="anarres molecular",
        description="Qualify molecular sources and inspect released Q07820 evidence.",
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
        "source-digest", help="Compute the revision of a native molecular environment."
    )
    source_digest.add_argument("--source", type=Path, required=True)
    source_digest.add_argument("--json", action="store_true")
    source_digest.set_defaults(handler=command_source_digest)

    qualify_source = commands.add_parser(
        "qualify-source", help="Validate a native molecular environment."
    )
    qualify_source.add_argument("--manifest", type=Path, required=True)
    qualify_source.add_argument("--json", action="store_true")
    qualify_source.set_defaults(handler=command_qualify_source)

    probe_source = commands.add_parser(
        "probe-source", help="Plan or explicitly execute the released Q07820 endpoint."
    )
    probe_source.add_argument("--manifest", type=Path, required=True)
    probe_source.add_argument("--policy", required=True)
    probe_source.add_argument("--policy-revision", required=True)
    probe_source.add_argument("--output", type=Path, required=True)
    probe_source.add_argument("--repository", type=Path)
    probe_source.add_argument("--sampler-python", type=Path, default=Path(sys.executable))
    probe_source.add_argument("--oracle-python", type=Path, default=Path(sys.executable))
    probe_source.add_argument("--device", default="cuda")
    probe_source.add_argument("--docking-jobs", type=int, default=8)
    probe_source.add_argument("--metric-jobs", type=int, default=8)
    probe_source.add_argument("--execute", action="store_true")
    probe_source.add_argument("--force", action="store_true")
    probe_source.add_argument("--json", action="store_true")
    probe_source.set_defaults(handler=command_probe_source)

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
        MolecularProbeError,
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
