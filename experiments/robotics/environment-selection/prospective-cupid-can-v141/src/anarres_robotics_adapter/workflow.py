"""Portable execution primitives for the frozen Can v1.4.1 comparison."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CURAEVAL_REVISION = "bd94bbbd435c1ef55edfe244894e5468f3a5df2b"
SOURCE_DATASET_SHA256 = "b6ceaed84c0335613a5001c900493b226481c132c792ec2cbdb99cb12c62baf0"
CANDIDATE_FREEZE_SHA256 = "3b3b34e544dd5a1ce0740fb534a7fb0f5213f89173e657e6889b9e9e16ff5c8f"
REQUIRED_TRAINING_MODULES = ("torch", "robomimic", "robosuite", "mujoco")
MASK_KEYS = {
    "random_50": "anarres_random_50",
    "length_50": "anarres_length_50",
    "cupid_50": "anarres_cupid_50",
    "cupid_tier_balanced_50": "anarres_cupid_tier_balanced_50",
}


class WorkflowError(ValueError):
    """Raised when a workflow input violates the frozen contract."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def object_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def argv_sha256(argv: list[str]) -> str:
    payload = json.dumps(argv, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def demo_number(name: str) -> int:
    prefix, separator, suffix = name.rpartition("_")
    if prefix != "demo" or separator != "_" or not suffix.isdigit():
        raise WorkflowError(f"invalid demonstration identity: {name}")
    return int(suffix)


def membership_hash(names: list[str]) -> str:
    payload = "\n".join(sorted(names, key=demo_number)) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def read_candidates(path: Path) -> dict[str, Any]:
    if file_sha256(path) != CANDIDATE_FREEZE_SHA256:
        raise WorkflowError("candidate artifact does not match the frozen public record")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    if frozen.get("status") != "CANDIDATES_FROZEN__OUTCOMES_UNOPENED":
        raise WorkflowError("candidate artifact is not frozen")
    if frozen.get("outcomes_read") is not False:
        raise WorkflowError("candidate artifact reports outcome access")
    expected = {"all_data", *MASK_KEYS}
    if set(frozen.get("candidates", {})) != expected:
        raise WorkflowError("candidate identities differ from the frozen comparison")
    for candidate_id, record in frozen["candidates"].items():
        members = record["members"]
        if len(members) != record["count"] or len(set(members)) != len(members):
            raise WorkflowError(f"invalid member count for {candidate_id}")
        if membership_hash(members) != record["membership_sha256"]:
            raise WorkflowError(f"membership hash mismatch for {candidate_id}")
    return frozen


def prepare_dataset(source: Path, output: Path, candidates_path: Path) -> dict[str, Any]:
    import h5py

    if source.resolve() == output.resolve():
        raise WorkflowError("prepared dataset must not overwrite the source dataset")
    if file_sha256(source) != SOURCE_DATASET_SHA256:
        raise WorkflowError("source dataset does not match the pinned Can v1.4.1 artifact")
    frozen = read_candidates(candidates_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    shutil.copy2(source, output)
    try:
        with h5py.File(output, "a") as dataset:
            masks = dataset.require_group("mask")
            known = set(dataset["data"].keys())
            for candidate_id, mask_key in MASK_KEYS.items():
                members = sorted(frozen["candidates"][candidate_id]["members"], key=demo_number)
                unknown = set(members) - known
                if unknown:
                    raise WorkflowError(
                        f"{candidate_id} contains unknown demonstrations: {sorted(unknown)[:3]}"
                    )
                if mask_key in masks:
                    del masks[mask_key]
                masks.create_dataset(mask_key, data=[member.encode() for member in members])
            dataset.attrs["anarres_candidate_freeze_sha256"] = file_sha256(candidates_path)
            dataset.attrs["anarres_source_dataset_sha256"] = SOURCE_DATASET_SHA256
    except Exception:
        output.unlink(missing_ok=True)
        raise
    output.chmod(0o444)
    return {
        "status": "prepared",
        "dataset": str(output),
        "dataset_sha256": f"sha256:{file_sha256(output)}",
        "source_dataset_sha256": f"sha256:{SOURCE_DATASET_SHA256}",
        "candidate_freeze_sha256": f"sha256:{file_sha256(candidates_path)}",
        "filter_keys": {"all_data": "none", **MASK_KEYS},
        "candidate_outcomes_opened": False,
    }


def validate_plan(plan: dict[str, Any]) -> None:
    recorded = plan.get("plan_digest")
    unsigned = dict(plan)
    unsigned.pop("plan_digest", None)
    if recorded != f"sha256:{object_sha256(unsigned)}":
        raise WorkflowError("workflow plan digest mismatch")
    if plan.get("scientific_boundary", {}).get("candidate_outcomes_opened") is not False:
        raise WorkflowError("workflow plan does not preserve sealed outcomes")


def validate_plan_candidates(
    plan: dict[str, Any], frozen: dict[str, Any], candidates_path: Path
) -> None:
    inputs = {item["role"]: item["digest"] for item in plan["inputs"]}
    expected_digest = f"sha256:{file_sha256(candidates_path)}"
    if inputs.get("frozen_candidates") != expected_digest:
        raise WorkflowError("workflow plan references a different candidate freeze")
    for run in plan["candidate_runs"]:
        candidate_id = run["candidate_id"]
        expected_membership = frozen["candidates"][candidate_id]["membership_sha256"]
        if run["membership_sha256"] != f"sha256:{expected_membership}":
            raise WorkflowError(f"workflow membership mismatch for {candidate_id}")


def validate_curaeval_checkout(path: Path) -> None:
    script = path / "scripts/run_dp.py"
    if not script.is_file():
        raise WorkflowError("CuraEval checkout is missing scripts/run_dp.py")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=False
    )
    if result.returncode != 0 or result.stdout.strip() != CURAEVAL_REVISION:
        raise WorkflowError(f"CuraEval must be checked out at {CURAEVAL_REVISION}")


def validate_prepared_dataset(path: Path, candidates_path: Path) -> None:
    import h5py

    frozen = read_candidates(candidates_path)
    with h5py.File(path, "r") as dataset:
        if dataset.attrs.get("anarres_source_dataset_sha256") != SOURCE_DATASET_SHA256:
            raise WorkflowError("dataset was not prepared from the pinned source artifact")
        known = set(dataset["data"].keys())
        for candidate_id, mask_key in MASK_KEYS.items():
            observed = [value.decode() for value in dataset["mask"][mask_key][()]]
            expected = sorted(frozen["candidates"][candidate_id]["members"], key=demo_number)
            if observed != expected or set(observed) - known:
                raise WorkflowError(f"prepared mask mismatch for {candidate_id}")


def task_records(
    plan: dict[str, Any], dataset: Path, curaeval: Path, output_root: Path, python: str
) -> list[dict[str, Any]]:
    records = []
    for index, run in enumerate(plan["candidate_runs"]):
        run_root = output_root / "runs" / run["run_id"]
        records.append(
            {
                "task_index": index,
                "run_id": run["run_id"],
                "candidate_id": run["candidate_id"],
                "seed": run["seed"],
                "filter_key": MASK_KEYS.get(run["candidate_id"], "none"),
                "evaluation_episodes": run["evaluation_episodes"],
                "evaluation_horizon": run["evaluation_horizon"],
                "evaluation_seed": plan["evaluation_contract"]["environment_seed"],
                "train_argv": [
                    python,
                    str(curaeval / "scripts/run_dp.py"),
                    "--dataset",
                    str(dataset),
                    "--filter_key",
                    MASK_KEYS.get(run["candidate_id"], "none"),
                    "--name",
                    run["run_id"],
                    "--output_dir",
                    str(run_root / "training"),
                    "--seed",
                    str(run["seed"]),
                    "--epochs",
                    str(plan["training_contract"]["epochs"]),
                    "--steps_per_epoch",
                    str(plan["training_contract"]["steps_per_epoch"]),
                    "--batch_size",
                    str(plan["training_contract"]["batch_size"]),
                    "--rollout_n",
                    "50",
                    "--horizon",
                    str(run["evaluation_horizon"]),
                    "--fast",
                ],
                "run_root": str(run_root),
            }
        )
    return records


def runtime_fingerprint(python: str) -> dict[str, Any]:
    identity = subprocess.run(
        [
            python,
            "-c",
            (
                "import json,platform,sys;"
                "import importlib.util;"
                "import importlib.metadata as md;"
                f"mods={REQUIRED_TRAINING_MODULES!r};"
                "pkgs=sorted((d.metadata.get('Name','')+'=='+d.version+'|'"
                "+(d.read_text('direct_url.json') or '')).strip() for d in md.distributions());"
                "print(json.dumps({'executable':sys.executable,'python':sys.version,"
                "'platform':platform.platform(),'missing_modules':"
                "[m for m in mods if importlib.util.find_spec(m) is None],"
                "'packages':pkgs}))"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if identity.returncode != 0:
        raise WorkflowError(f"cannot inspect Python runtime: {identity.stderr.strip()}")
    result = json.loads(identity.stdout)
    frozen = result["packages"]
    result.update(
        {
            "host_platform": platform.platform(),
            "packages": frozen,
            "packages_sha256": hashlib.sha256(("\n".join(frozen) + "\n").encode()).hexdigest(),
        }
    )
    return result


def visible_accelerators() -> list[str]:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise WorkflowError("nvidia-smi could not identify the allocated accelerator")
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not names:
        raise WorkflowError("no NVIDIA accelerator is visible")
    return names


def write_bundle(
    plan_path: Path,
    dataset: Path,
    candidates_path: Path,
    curaeval: Path,
    output: Path,
    python: str,
    backend: str,
    max_parallel: int,
    accelerator_name: str,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_plan(plan)
    frozen = read_candidates(candidates_path)
    validate_plan_candidates(plan, frozen, candidates_path)
    validate_curaeval_checkout(curaeval)
    validate_prepared_dataset(dataset, candidates_path)
    if backend not in {"local", "slurm"}:
        raise WorkflowError("backend must be local or slurm")
    if max_parallel < 1:
        raise WorkflowError("max_parallel must be at least one")
    if not accelerator_name.strip():
        raise WorkflowError("accelerator_name must identify the fixed GPU model")
    runtime = runtime_fingerprint(python)
    if runtime["missing_modules"]:
        raise WorkflowError(
            "training runtime is missing required modules: " + ", ".join(runtime["missing_modules"])
        )
    output.mkdir(parents=True)
    records = task_records(plan, dataset.resolve(), curaeval.resolve(), output.resolve(), python)
    normalized_plan = output / "PLAN.json"
    normalized_plan.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = output / "tasks.jsonl"
    manifest.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    (output / "RUNTIME.json").write_text(
        json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    launcher = output / ("run-local.sh" if backend == "local" else "submit-slurm.sh")
    cli_prefix = (
        f"{shlex.quote(sys.executable)} -m anarres_robotics_adapter.cli run-task "
        f"--bundle {shlex.quote(str(output.resolve()))}"
    )
    if backend == "local":
        body = f"""#!/bin/sh
set -eu
for i in $(seq 0 {len(records) - 1}); do
  {cli_prefix} --task-index "$i" --stage train --execute
done
for i in $(seq 0 {len(records) - 1}); do
  {cli_prefix} --task-index "$i" --stage evaluate --execute
done
"""
    else:
        train_wrap = shlex.quote(
            f"{cli_prefix} --task-index $SLURM_ARRAY_TASK_ID --stage train --execute"
        )
        evaluate_wrap = shlex.quote(
            f"{cli_prefix} --task-index $SLURM_ARRAY_TASK_ID --stage evaluate --execute"
        )
        body = f"""#!/bin/sh
set -eu
ROOT={shlex.quote(str(output.resolve()))}
TRAIN=$(sbatch --parsable --array=0-{len(records) - 1}%{max_parallel} \\
  --gres=gpu:1 --cpus-per-task=8 --mem=48G --time=06:00:00 --wrap={train_wrap})
sbatch --array=0-{len(records) - 1}%{max_parallel} --dependency=afterok:$TRAIN \\
  --gres=gpu:1 --cpus-per-task=4 --mem=24G --time=03:00:00 --wrap={evaluate_wrap}
"""
    launcher.write_text(body, encoding="utf-8")
    launcher.chmod(0o755)
    provenance = {
        "schema_version": "anarres.robotics-execution-bundle.v1",
        "plan_digest": plan["plan_digest"],
        "backend": backend,
        "task_count": len(records),
        "dataset": str(dataset.resolve()),
        "dataset_sha256": f"sha256:{file_sha256(dataset)}",
        "curaeval": str(curaeval.resolve()),
        "candidate_freeze_sha256": f"sha256:{file_sha256(candidates_path)}",
        "curaeval_revision": CURAEVAL_REVISION,
        "frozen_point_prediction": plan["scientific_boundary"]["frozen_point_prediction"],
        "expected_evaluation_episodes": plan["totals"]["evaluation_episodes"],
        "python_executable": python,
        "accelerator_name": accelerator_name.strip(),
        "runtime_sha256": f"sha256:{file_sha256(output / 'RUNTIME.json')}",
        "bound_files": {
            "plan": f"sha256:{file_sha256(normalized_plan)}",
            "runtime": f"sha256:{file_sha256(output / 'RUNTIME.json')}",
            "tasks": f"sha256:{file_sha256(manifest)}",
            "launcher": f"sha256:{file_sha256(launcher)}",
        },
        "execution_started": False,
        "candidate_outcomes_opened": False,
    }
    provenance["bundle_digest"] = f"sha256:{object_sha256(provenance)}"
    (output / "BUNDLE.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "status": "bundled",
        "bundle": str(output),
        "backend": backend,
        "task_count": len(records),
        "launcher": str(launcher),
        "execution_started": False,
        "candidate_outcomes_opened": False,
    }


def validate_bundle(bundle: Path, *, check_dataset: bool = False) -> tuple[dict, dict, list[dict]]:
    provenance = json.loads((bundle / "BUNDLE.json").read_text(encoding="utf-8"))
    recorded_digest = provenance.get("bundle_digest")
    unsigned = dict(provenance)
    unsigned.pop("bundle_digest", None)
    if recorded_digest != f"sha256:{object_sha256(unsigned)}":
        raise WorkflowError("execution bundle digest mismatch")
    backend = provenance.get("backend")
    if backend not in {"local", "slurm"}:
        raise WorkflowError("execution bundle has an invalid backend")
    paths = {
        "plan": bundle / "PLAN.json",
        "runtime": bundle / "RUNTIME.json",
        "tasks": bundle / "tasks.jsonl",
        "launcher": bundle / ("run-local.sh" if backend == "local" else "submit-slurm.sh"),
    }
    for role, path in paths.items():
        expected = provenance.get("bound_files", {}).get(role)
        if not path.is_file() or expected != f"sha256:{file_sha256(path)}":
            raise WorkflowError(f"bound {role} artifact differs from the execution bundle")
    plan = json.loads(paths["plan"].read_text(encoding="utf-8"))
    validate_plan(plan)
    if plan["plan_digest"] != provenance.get("plan_digest"):
        raise WorkflowError("bound plan differs from the execution bundle")
    tasks = [json.loads(line) for line in paths["tasks"].read_text(encoding="utf-8").splitlines()]
    if len(tasks) != provenance.get("task_count") or len(tasks) != plan["totals"]["candidate_runs"]:
        raise WorkflowError("bound task count differs from the frozen plan")
    if sum(task["evaluation_episodes"] for task in tasks) != plan["totals"]["evaluation_episodes"]:
        raise WorkflowError("bound evaluation count differs from the frozen plan")
    expected_tasks = task_records(
        plan,
        Path(provenance["dataset"]),
        Path(provenance["curaeval"]),
        bundle,
        provenance["python_executable"],
    )
    if tasks != expected_tasks:
        raise WorkflowError("bound tasks differ from the frozen plan")
    if provenance.get("runtime_sha256") != provenance.get("bound_files", {}).get("runtime"):
        raise WorkflowError("runtime identity differs within the execution bundle")
    frozen_input = next(
        (item["digest"] for item in plan["inputs"] if item["role"] == "frozen_candidates"),
        None,
    )
    if provenance.get("candidate_freeze_sha256") != frozen_input:
        raise WorkflowError("candidate identity differs within the execution bundle")
    if check_dataset:
        dataset = Path(provenance["dataset"])
        if not dataset.is_file() or provenance.get("dataset_sha256") != (
            f"sha256:{file_sha256(dataset)}"
        ):
            raise WorkflowError("prepared dataset differs from the execution bundle")
    return provenance, plan, tasks


def load_task(bundle: Path, task_index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    provenance, _, tasks = validate_bundle(bundle)
    if task_index < 0 or task_index >= len(tasks):
        raise WorkflowError("task index is outside the execution bundle")
    return provenance, tasks[task_index]


def submit_bundle(bundle: Path, execute: bool) -> dict[str, Any]:
    if not execute:
        raise WorkflowError("submission requires --execute")
    provenance, _, _ = validate_bundle(bundle, check_dataset=True)
    backend = provenance["backend"]
    launcher = bundle / ("run-local.sh" if backend == "local" else "submit-slurm.sh")
    if not launcher.is_file():
        raise WorkflowError(f"bundle launcher is missing: {launcher}")
    completed = subprocess.run(
        [str(launcher)], cwd=bundle, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise WorkflowError(
            f"{backend} submission failed: {(completed.stderr or completed.stdout).strip()}"
        )
    return {
        "status": "complete" if backend == "local" else "submitted",
        "backend": backend,
        "launcher": str(launcher),
        "scheduler_output": completed.stdout.strip(),
        "execution_started": True,
        "candidate_outcomes_opened": False,
    }


def find_checkpoint(run_root: Path) -> Path:
    checkpoints = sorted((run_root / "training").rglob("last.pth"))
    if len(checkpoints) != 1:
        raise WorkflowError(f"expected one final checkpoint, found {len(checkpoints)}")
    return checkpoints[0]


def evaluation_argv(task: dict[str, Any], checkpoint: Path) -> list[str]:
    return [
        task["train_argv"][0],
        "-m",
        "robomimic.scripts.run_trained_agent",
        "--agent",
        str(checkpoint),
        "--n_rollouts",
        str(task["evaluation_episodes"]),
        "--horizon",
        str(task["evaluation_horizon"]),
        "--seed",
        str(task["evaluation_seed"]),
    ]


def run_task(bundle: Path, task_index: int, stage: str, execute: bool) -> dict[str, Any]:
    if not execute:
        raise WorkflowError("execution requires --execute")
    provenance, task = load_task(bundle, task_index)
    expected_runtime = json.loads((bundle / "RUNTIME.json").read_text(encoding="utf-8"))
    observed_runtime = runtime_fingerprint(task["train_argv"][0])
    if (
        observed_runtime["python"] != expected_runtime["python"]
        or observed_runtime["packages_sha256"] != expected_runtime["packages_sha256"]
        or observed_runtime["missing_modules"]
    ):
        raise WorkflowError("execution runtime differs from the bound runtime lock")
    accelerator_names = visible_accelerators()
    if any(name != provenance["accelerator_name"] for name in accelerator_names):
        raise WorkflowError(
            "allocated accelerator differs from the bundle contract: "
            + ", ".join(accelerator_names)
        )
    run_root = Path(task["run_root"])
    run_root.mkdir(parents=True, exist_ok=True)
    if stage == "train":
        argv = task["train_argv"]
        log_path = run_root / "train.log"
        record_path = run_root / "TRAIN_COMPLETE.json"
    elif stage == "evaluate":
        train_record_path = run_root / "TRAIN_COMPLETE.json"
        if not train_record_path.is_file():
            raise WorkflowError("evaluation requires a verified training completion record")
        train_record = json.loads(train_record_path.read_text())
        checkpoint = find_checkpoint(run_root)
        if train_record.get("checkpoint_sha256") != f"sha256:{file_sha256(checkpoint)}":
            raise WorkflowError("final checkpoint differs from its training completion record")
        argv = evaluation_argv(task, checkpoint)
        log_path = run_root / "evaluation.log"
        record_path = run_root / "EVALUATION_COMPLETE.json"
    else:
        raise WorkflowError("stage must be train or evaluate")
    if record_path.exists():
        raise WorkflowError(f"completion record already exists: {record_path}")
    with log_path.open("wb") as log:
        completed = subprocess.run(
            argv,
            cwd=Path(task["train_argv"][1]).parents[1],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            check=False,
        )
    if completed.returncode != 0:
        raise WorkflowError(f"{stage} failed for {task['run_id']}; see {log_path}")
    record: dict[str, Any] = {
        "schema_version": "anarres.robotics-task-completion.v1",
        "plan_digest": provenance["plan_digest"],
        "run_id": task["run_id"],
        "task_index": task_index,
        "stage": stage,
        "log_sha256": f"sha256:{file_sha256(log_path)}",
        "runtime_sha256": provenance["runtime_sha256"],
        "accelerator_name": provenance["accelerator_name"],
        "task_sha256": f"sha256:{object_sha256(task)}",
        "command_sha256": f"sha256:{argv_sha256(argv)}",
    }
    if stage == "train":
        checkpoint = find_checkpoint(run_root)
        record["checkpoint"] = str(checkpoint)
        record["checkpoint_sha256"] = f"sha256:{file_sha256(checkpoint)}"
    else:
        record["checkpoint_sha256"] = f"sha256:{file_sha256(checkpoint)}"
        record["evaluation_episodes"] = task["evaluation_episodes"]
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return {"status": "complete", **record}


def gate_record(bundle: Path) -> dict[str, Any]:
    provenance, _, tasks = validate_bundle(bundle, check_dataset=True)
    records = []
    for task in tasks:
        run_root = Path(task["run_root"])
        for name in ("TRAIN_COMPLETE.json", "EVALUATION_COMPLETE.json"):
            path = run_root / name
            if not path.is_file():
                raise WorkflowError(f"release gate is incomplete: {path}")
            record = json.loads(path.read_text())
            if record.get("plan_digest") != provenance["plan_digest"]:
                raise WorkflowError(f"plan identity mismatch: {path}")
            if record.get("run_id") != task["run_id"]:
                raise WorkflowError(f"run identity mismatch: {path}")
            if record.get("runtime_sha256") != provenance["runtime_sha256"]:
                raise WorkflowError(f"runtime identity mismatch: {path}")
            if record.get("accelerator_name") != provenance["accelerator_name"]:
                raise WorkflowError(f"accelerator identity mismatch: {path}")
            if record.get("task_sha256") != f"sha256:{object_sha256(task)}":
                raise WorkflowError(f"task identity mismatch: {path}")
            log_path = run_root / ("train.log" if name.startswith("TRAIN") else "evaluation.log")
            if record.get("log_sha256") != f"sha256:{file_sha256(log_path)}":
                raise WorkflowError(f"log identity mismatch: {path}")
            checkpoint = find_checkpoint(run_root)
            if record.get("checkpoint_sha256") != f"sha256:{file_sha256(checkpoint)}":
                raise WorkflowError(f"checkpoint identity mismatch: {path}")
            expected_argv = (
                task["train_argv"]
                if name.startswith("TRAIN")
                else evaluation_argv(task, checkpoint)
            )
            if record.get("command_sha256") != f"sha256:{argv_sha256(expected_argv)}":
                raise WorkflowError(f"command identity mismatch: {path}")
            if (
                name.startswith("EVALUATION")
                and record.get("evaluation_episodes") != task["evaluation_episodes"]
            ):
                raise WorkflowError(f"evaluation count mismatch: {path}")
            records.append({"path": str(path), "sha256": f"sha256:{file_sha256(path)}"})
    gate = {
        "schema_version": "anarres.robotics-release-gate.v1",
        "plan_digest": provenance["plan_digest"],
        "candidate_runs": len(tasks),
        "evaluation_episodes": sum(task["evaluation_episodes"] for task in tasks),
        "complete": True,
        "records": records,
        "candidate_outcomes_opened": False,
    }
    if gate["evaluation_episodes"] != provenance["expected_evaluation_episodes"]:
        raise WorkflowError("evaluation episode count differs from the frozen bundle")
    return gate


def release_gate(bundle: Path) -> dict[str, Any]:
    gate = gate_record(bundle)
    output = bundle / "RELEASE_GATE.json"
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    return {"status": "pass", "release_gate": str(output), **gate}


ROLLOUT_STATS = re.compile(r"Average Rollout Stats\s*(\{.*?\})", re.S)


def parse_success_rate(path: Path) -> float:
    match = ROLLOUT_STATS.search(path.read_text(encoding="utf-8", errors="replace"))
    if match is None:
        raise WorkflowError(f"evaluation log has no rollout statistics: {path}")
    try:
        stats = json.loads(match.group(1))
        rate = float(stats["Success_Rate"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise WorkflowError(f"evaluation log has invalid rollout statistics: {path}") from error
    if not 0.0 <= rate <= 1.0:
        raise WorkflowError(f"evaluation success rate is outside [0, 1]: {path}")
    return rate


def score_bundle(bundle: Path) -> dict[str, Any]:
    gate_path = bundle / "RELEASE_GATE.json"
    if not gate_path.is_file():
        raise WorkflowError("scoring requires a passing release gate")
    observed_gate = json.loads(gate_path.read_text(encoding="utf-8"))
    expected_gate = gate_record(bundle)
    if observed_gate != expected_gate:
        raise WorkflowError("release gate no longer matches the completed artifacts")
    provenance, _, tasks = validate_bundle(bundle, check_dataset=True)
    rates: dict[str, list[float]] = {}
    for task in tasks:
        rate = parse_success_rate(Path(task["run_root"]) / "evaluation.log")
        rates.setdefault(task["candidate_id"], []).append(rate)
    means = {candidate: sum(values) / len(values) for candidate, values in rates.items()}
    prediction = provenance["frozen_point_prediction"]
    if prediction not in means:
        raise WorkflowError("frozen point prediction is absent from the completed candidates")
    best_mean = max(means.values())
    winners = sorted(candidate for candidate, mean in means.items() if mean == best_mean)
    result = {
        "schema_version": "anarres.robotics-prospective-result.v1",
        "plan_digest": provenance["plan_digest"],
        "frozen_point_prediction": prediction,
        "observed_best": winners,
        "prediction_is_observed_best": prediction in winners,
        "allocation_regret_pp": 100.0 * (best_mean - means[prediction]),
        "mean_success_rate": means,
        "seed_success_rates": rates,
        "candidate_runs": len(tasks),
        "evaluation_episodes": expected_gate["evaluation_episodes"],
        "candidate_outcomes_opened": True,
    }
    output = bundle / "RESULT.json"
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return {"status": "scored", "result": str(output), **result}
