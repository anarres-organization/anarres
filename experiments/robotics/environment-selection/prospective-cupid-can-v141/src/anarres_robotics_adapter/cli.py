"""Task-oriented CLI for the released CUPID Can v1.4.1 measurements."""

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

from . import workflow


class RoboticsCliError(ValueError):
    """Raised when a released robotics workflow cannot be verified."""


def adapter_descriptor() -> dict[str, Any]:
    """Describe the adapter without opening study artifacts."""

    return {
        "schema_version": "anarres.adapter-descriptor.v1",
        "name": "robotics",
        "version": "0.4.0",
        "protocol_version": 1,
        "domain": "robotics",
        "executable": "anarres-robotics",
        "profile_schema_versions": ["anarres.environment-profile-input.v1"],
        "capabilities": [
            "bundle",
            "gate",
            "plan",
            "prepare",
            "profile",
            "results",
            "run-task",
            "score",
            "status",
            "submit",
            "verify",
        ],
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


def pusht_root(repository: Path) -> Path:
    return repository / "experiments/robotics/environment-selection/prospective-pusht"


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
        "freeze": root / "FREEZE.json",
        "freeze_correction": root / "FREEZE_CORRECTION.json",
        "candidates": root / "CANDIDATES.json",
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
        "sources": sources,
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
        "selector_performance_validated": False,
        "profile_coordinates": [
            "mean_cupid_rank_percentile",
            "operator_tier_effective_coverage",
            "mean_demonstration_action_steps",
            "measurement_rank_reliability",
        ],
        "profile_context": [
            "candidate_construction",
            "tier_balance_constraint_applied",
            "selected_fraction",
            "starting_policy_failure_rate",
            "score_missingness_rate",
        ],
        "profile_ready": (
            qualification.get("passed") is True
            and measurements["measurement"]["reliability_gate_passed"] is True
            and measurements["outcomes_read"] is False
        ),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def sha256_object(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def build_workflow_plan(repository: Path) -> dict[str, Any]:
    _, records = validate_native(repository)
    paths = native_paths(repository)
    protocol = records["protocol"]
    measurements = records["measurements"]
    qualification = records["qualification"]

    if measurements["outcomes_read"] is not False:
        raise RoboticsCliError("candidate outcomes must remain sealed while planning")
    if qualification.get("passed") is not True:
        raise RoboticsCliError("closed-loop qualification did not pass")
    if measurements["measurement"]["reliability_gate_passed"] is not True:
        raise RoboticsCliError("influence measurement did not pass its reliability gate")

    candidates = measurements["candidates"]
    protocol_candidates = protocol["candidates"]
    candidate_ids = [candidate["id"] for candidate in protocol_candidates]
    if set(candidate_ids) != set(candidates):
        raise RoboticsCliError("candidate identities differ between protocol and measurement")

    seeds = protocol["training"]["seeds"]
    steps_per_run = protocol["training"]["epochs"] * protocol["training"]["steps_per_epoch"]
    candidate_runs = []
    for candidate in protocol_candidates:
        candidate_id = candidate["id"]
        measured = candidates[candidate_id]
        for seed in seeds:
            candidate_runs.append(
                {
                    "run_id": f"{candidate_id}__seed-{seed}",
                    "candidate_id": candidate_id,
                    "seed": seed,
                    "demonstration_count": candidate["count"],
                    "membership_sha256": f"sha256:{measured['membership_sha256']}",
                    "optimizer_steps": steps_per_run,
                    "evaluation_episodes": protocol["evaluation"]["rollouts_per_policy"],
                    "evaluation_horizon": protocol["evaluation"]["horizon"],
                }
            )

    expected_runs = protocol["release_gate"]["expected_candidate_runs"]
    expected_episodes = protocol["release_gate"]["expected_evaluation_episodes"]
    if len(candidate_runs) != expected_runs:
        raise RoboticsCliError("planned run count differs from the frozen release gate")
    if sum(run["evaluation_episodes"] for run in candidate_runs) != expected_episodes:
        raise RoboticsCliError("planned evaluation count differs from the frozen release gate")

    plan: dict[str, Any] = {
        "schema_version": "anarres.robotics-workflow-plan.v1",
        "plan_id": "prospective-cupid-can-v141-candidate-comparison",
        "domain": "robotics",
        "study_id": protocol["study_id"],
        "phase": "candidate_training_and_evaluation",
        "producer": {
            "kind": "domain-adapter",
            "id": "anarres-robotics",
            "revision": adapter_descriptor()["version"],
        },
        "inputs": [
            {
                "role": "frozen_candidates",
                "uri": "release://prospective-cupid-can-v141/CANDIDATES.json",
                "digest": sha256_file(paths["candidates"]),
            },
            {
                "role": "protocol",
                "uri": "release://prospective-cupid-can-v141/PROTOCOL.json",
                "digest": sha256_file(paths["protocol"]),
            },
            {
                "role": "sources",
                "uri": "release://prospective-cupid-can-v141/SOURCES.json",
                "digest": sha256_file(paths["sources"]),
            },
            {
                "role": "qualification",
                "uri": "release://prospective-cupid-can-v141/QUALIFICATION.json",
                "digest": sha256_file(paths["qualification"]),
            },
            {
                "role": "pre_outcome_measurements",
                "uri": "release://prospective-cupid-can-v141/PROFILE_MEASUREMENTS.json",
                "digest": sha256_file(paths["measurements"]),
            },
            {
                "role": "original_freeze",
                "uri": "release://prospective-cupid-can-v141/FREEZE.json",
                "digest": sha256_file(paths["freeze"]),
            },
            {
                "role": "freeze_correction",
                "uri": "release://prospective-cupid-can-v141/FREEZE_CORRECTION.json",
                "digest": sha256_file(paths["freeze_correction"]),
            },
        ],
        "execution": {
            "mode": "plan_only",
            "execution_started": False,
            "submission_ready": False,
            "submission_requires_explicit_command": True,
            "scheduler": None,
            "blockers": [
                "runtime_environment_not_bound",
                "scheduler_binding_not_selected",
            ],
        },
        "resource_contract": {
            "accelerator": protocol["training"]["hardware_rule"],
            "software_environment": "fixed_across_all_candidate_runs",
            "adaptive_stopping": protocol["training"]["adaptive_stopping"],
            "scheduler_specific_fields_present": False,
        },
        "training_contract": {
            "epochs": protocol["training"]["epochs"],
            "steps_per_epoch": protocol["training"]["steps_per_epoch"],
            "batch_size": protocol["training"]["batch_size"],
            "equal_optimizer_steps_across_arms": protocol["training"][
                "equal_optimizer_steps_across_arms"
            ],
            "checkpoint_rule": protocol["training"]["checkpoint_rule"],
            "adaptive_stopping": protocol["training"]["adaptive_stopping"],
        },
        "evaluation_contract": {
            "rollouts_per_policy": protocol["evaluation"]["rollouts_per_policy"],
            "horizon": protocol["evaluation"]["horizon"],
            "environment_seed": protocol["evaluation"]["environment_seed"],
            "terminate_on_success": protocol["evaluation"]["terminate_on_success"],
            "primary_outcome": protocol["evaluation"]["primary_outcome"],
            "primary_unit": protocol["evaluation"]["primary_unit"],
            "paired_initial_conditions_across_arms": protocol["evaluation"][
                "paired_initial_conditions_across_arms"
            ],
        },
        "release_gate": {
            "expected_candidate_runs": expected_runs,
            "expected_evaluation_episodes": expected_episodes,
            "require_all_arms_and_seeds": protocol["release_gate"]["require_all_arms_and_seeds"],
            "require_membership_hashes": protocol["release_gate"]["require_membership_hashes"],
            "require_checkpoint_hashes": protocol["release_gate"]["require_checkpoint_hashes"],
            "require_outcome_file_hashes": protocol["release_gate"]["require_outcome_file_hashes"],
        },
        "stages": [
            {
                "stage_id": "preflight",
                "kind": "validate_frozen_inputs",
                "depends_on": [],
                "task_count": 1,
                "opens_candidate_outcomes": False,
            },
            {
                "stage_id": "train",
                "kind": "candidate_policy_training",
                "depends_on": ["preflight"],
                "task_count": expected_runs,
                "opens_candidate_outcomes": False,
            },
            {
                "stage_id": "evaluate",
                "kind": "paired_closed_loop_evaluation",
                "depends_on": ["train"],
                "task_count": expected_runs,
                "opens_candidate_outcomes": False,
            },
            {
                "stage_id": "release_gate",
                "kind": "completeness_and_identity_gate",
                "depends_on": ["evaluate"],
                "task_count": 1,
                "opens_candidate_outcomes": False,
            },
            {
                "stage_id": "score",
                "kind": "prospective_decision_scoring",
                "depends_on": ["release_gate"],
                "task_count": 1,
                "opens_candidate_outcomes": True,
            },
        ],
        "candidate_runs": candidate_runs,
        "totals": {
            "candidate_arms": len(candidate_ids),
            "training_seeds_per_arm": len(seeds),
            "candidate_runs": expected_runs,
            "optimizer_steps": expected_runs * steps_per_run,
            "evaluation_episodes": expected_episodes,
        },
        "scientific_boundary": {
            "candidate_outcomes_opened": False,
            "frozen_point_prediction": measurements["decision"],
            "primary_outcome": protocol["evaluation"]["primary_outcome"],
            "primary_unit": protocol["evaluation"]["primary_unit"],
            "no_outcome_driven_revision": protocol["decision"]["no_outcome_driven_revision"],
            "release_gate_precedes_scoring": True,
        },
    }
    plan["plan_digest"] = sha256_object(plan)
    return plan


def command_plan(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    plan = build_workflow_plan(repository)
    output = args.output.resolve()
    if output.exists() and not args.force:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "planned",
        "plan": str(output),
        "plan_digest": plan["plan_digest"],
        "candidate_runs": plan["totals"]["candidate_runs"],
        "evaluation_episodes": plan["totals"]["evaluation_episodes"],
        "submission_ready": plan["execution"]["submission_ready"],
        "blockers": plan["execution"]["blockers"],
        "execution_started": False,
        "candidate_outcomes_opened": False,
    }


def command_prepare(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    validate_native(repository)
    return workflow.prepare_dataset(
        args.dataset.resolve(),
        args.output.resolve(),
        native_paths(repository)["candidates"],
    )


def command_bundle(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    validate_native(repository)
    provided_plan = json.loads(args.plan.read_text(encoding="utf-8"))
    expected_plan = build_workflow_plan(repository)
    if provided_plan != expected_plan:
        raise RoboticsCliError("workflow plan differs from the current frozen study contract")
    return workflow.write_bundle(
        plan_path=args.plan.resolve(),
        dataset=args.dataset.resolve(),
        candidates_path=native_paths(repository)["candidates"],
        curaeval=args.curaeval.resolve(),
        output=args.output.resolve(),
        python=args.python,
        backend=args.backend,
        max_parallel=args.max_parallel,
        accelerator_name=args.accelerator_name,
        gpu_indices=[int(value) for value in args.gpu_indices.split(",") if value.strip()],
    )


def command_run_task(args: argparse.Namespace) -> dict[str, Any]:
    return workflow.run_task(args.bundle.resolve(), args.task_index, args.stage, args.execute)


def command_submit(args: argparse.Namespace) -> dict[str, Any]:
    return workflow.submit_bundle(args.bundle.resolve(), args.execute)


def command_gate(args: argparse.Namespace) -> dict[str, Any]:
    return workflow.release_gate(args.bundle.resolve())


def command_score(args: argparse.Namespace) -> dict[str, Any]:
    return workflow.score_bundle(args.bundle.resolve())


def load_pusht_reproducer(repository: Path) -> ModuleType:
    path = pusht_root(repository) / "scripts/reproduce.py"
    specification = importlib.util.spec_from_file_location(
        "anarres_robotics_pusht_reproducer", path
    )
    if specification is None or specification.loader is None:
        raise RoboticsCliError(f"cannot load PushT reproducer: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def command_results(args: argparse.Namespace) -> dict[str, Any]:
    repository = repository_root(args.repository)
    root = pusht_root(repository)
    outcomes_path = root / "data/outcomes.json"
    summary_path = root / "results/summary.json"
    reproducer_path = root / "scripts/reproduce.py"
    reproducer = load_pusht_reproducer(repository)
    outcomes = json.loads(outcomes_path.read_text(encoding="utf-8"))
    observed = reproducer.compute(outcomes)
    expected = json.loads(summary_path.read_text(encoding="utf-8"))
    if observed != expected:
        raise RoboticsCliError("recomputed PushT result differs from the released summary")
    return {
        "study_id": observed["artifact"],
        "domain": "robotics",
        "study": "prospective-pusht",
        "status": "released_prospective_result",
        "profile_input": False,
        "candidate_outcomes_opened": True,
        "frozen_action": observed["frozen_action"],
        "observed_best": observed["observed_best"],
        "abstention_correct": observed["abstention_correct"],
        "independent_training_seeds": observed["independent_training_seeds"],
        "means": observed["means"],
        "arm_regret_pp": observed["arm_regret_pp"],
        "contrasts": observed["contrasts"],
        "claim_boundary": (
            "The frozen abstention set retained the observed best arm in one PushT panel; "
            "correct abstention is not selector superiority."
        ),
        "artifacts": {
            "outcomes": sha256_file(outcomes_path),
            "summary": sha256_file(summary_path),
            "reproducer": sha256_file(reproducer_path),
        },
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
    first_plan = build_workflow_plan(repository)
    second_plan = build_workflow_plan(repository)
    with tempfile.TemporaryDirectory(prefix="anarres-robotics-verify-") as directory:
        root = Path(directory)
        first = export_profiles(repository, root / "first")
        second = export_profiles(repository, root / "second")
        deterministic = [path.read_bytes() for path in first] == [
            path.read_bytes() for path in second
        ]
        sizes = [path.stat().st_size for path in first]
    return {
        "status": "pass",
        "profile_count": len(first),
        "nonempty_profiles": all(size > 0 for size in sizes),
        "deterministic_profiles": deterministic,
        "deterministic_plan": first_plan == second_plan,
        "planned_candidate_runs": first_plan["totals"]["candidate_runs"],
        "submission_ready": first_plan["execution"]["submission_ready"],
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

    plan = commands.add_parser(
        "plan", help="Write a deterministic candidate-comparison workflow plan."
    )
    add_common(plan)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--force", action="store_true")
    plan.set_defaults(handler=command_plan)

    prepare = commands.add_parser(
        "prepare", help="Copy the pinned Can dataset and write all frozen candidate masks."
    )
    add_common(prepare)
    prepare.add_argument("--dataset", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.set_defaults(handler=command_prepare)

    bundle = commands.add_parser(
        "bundle", help="Bind a plan to prepared data, CuraEval, and a scheduler backend."
    )
    add_common(bundle)
    bundle.add_argument("--plan", type=Path, required=True)
    bundle.add_argument("--dataset", type=Path, required=True)
    bundle.add_argument("--curaeval", type=Path, required=True)
    bundle.add_argument("--output", type=Path, required=True)
    bundle.add_argument("--python", default=sys.executable)
    bundle.add_argument("--backend", choices=["local", "slurm"], default="local")
    bundle.add_argument("--max-parallel", type=int, default=1)
    bundle.add_argument("--accelerator-name", required=True)
    bundle.add_argument(
        "--gpu-indices",
        default="0",
        help="Comma-separated GPU indices for the local worker pool.",
    )
    bundle.set_defaults(handler=command_bundle)

    run_task_parser = commands.add_parser(
        "run-task", help="Execute one training or evaluation task from a bound bundle."
    )
    run_task_parser.add_argument("--bundle", type=Path, required=True)
    run_task_parser.add_argument("--task-index", type=int, required=True)
    run_task_parser.add_argument("--stage", choices=["train", "evaluate"], required=True)
    run_task_parser.add_argument("--execute", action="store_true")
    run_task_parser.add_argument("--json", action="store_true")
    run_task_parser.set_defaults(handler=command_run_task)

    submit = commands.add_parser(
        "submit", help="Start a bound local or Slurm workflow after explicit confirmation."
    )
    submit.add_argument("--bundle", type=Path, required=True)
    submit.add_argument("--execute", action="store_true")
    submit.add_argument("--json", action="store_true")
    submit.set_defaults(handler=command_submit)

    gate = commands.add_parser(
        "gate", help="Verify that every frozen training and evaluation task completed."
    )
    gate.add_argument("--bundle", type=Path, required=True)
    gate.add_argument("--json", action="store_true")
    gate.set_defaults(handler=command_gate)

    score = commands.add_parser(
        "score", help="Open and score outcomes only after the release gate passes."
    )
    score.add_argument("--bundle", type=Path, required=True)
    score.add_argument("--json", action="store_true")
    score.set_defaults(handler=command_score)

    profile = commands.add_parser("profile", help="Export native candidate profile inputs.")
    add_common(profile)
    profile.add_argument("--output-dir", type=Path, required=True)
    profile.add_argument("--force", action="store_true")
    profile.set_defaults(handler=command_profile)

    results = commands.add_parser(
        "results", help="Recompute the released prospective PushT decision report."
    )
    add_common(results)
    results.set_defaults(handler=command_results)

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
