#!/usr/bin/env python3
"""Run one frozen GPT-5.6 Sol queue entry through the qualified task-boundary route.

The runner refuses to start unless the protocol validates in this study directory, the
queue matches it, a separate authorization record binds both and sets a spend ceiling,
every earlier queue entry has a receipt, the output root belongs to that authorization,
and the Vero checkout matches the source pin. The attempt runs through the hash-pinned
harness unchanged.

Every run is recorded before it starts and again when it ends, so a run that never
finishes stays on the ledger as interrupted and is charged the authorization's reserve.
One infrastructure retry is allowed: a failure during grading regrades the preserved
workspace, and any other infrastructure failure or an interrupted run reruns the
attempt under a fresh run identity. Scientific and integrity outcomes are never retried.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

STUDY_ROOT = Path(__file__).resolve().parent
AUTHORIZATION_SCHEMA = "anarres.formal-verification-codex-sol-execution-authorization.v1"
STARTED_SCHEMA = "anarres.formal-verification-codex-sol-run-started.v1"
RUN_SCHEMA = "anarres.formal-verification-codex-sol-run.v1"
ROOT_MARKER = "measurement-root.json"
STOP_RECORD = "spend-ceiling-stop.json"
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
ERROR_CHARACTERS = 2000
COLLECTION_TIMEOUT = "workspace collection exceeded its time limit"


class QueueItemError(RuntimeError):
    """Raised when an entry cannot run without violating the frozen contract."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise QueueItemError(f"expected an object in {path.name}")
    return value


def write_new(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(name: str, filename: str) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, STUDY_ROOT / filename)
    if specification is None or specification.loader is None:
        raise QueueItemError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(specification)
    if str(STUDY_ROOT) not in sys.path:
        sys.path.insert(0, str(STUDY_ROOT))
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def validate_frozen_inputs(
    protocol_path: Path, queue_path: Path, authorization: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return the protocol, queue, and analysis once all three agree."""
    if protocol_path.resolve().parent != STUDY_ROOT:
        raise QueueItemError("the protocol must be validated in the directory that runs it")
    protocol = read_object(protocol_path)
    load("vero_codex_sol_queue_validator", "validate_codex_sol_probe_protocol.py").validate(
        protocol, STUDY_ROOT
    )
    queue = read_object(queue_path)
    panel_path = STUDY_ROOT / protocol["source"]["development_panel"]
    expected = load("vero_codex_sol_queue_builder", "build_probe_queue.py").build_queue(
        protocol,
        read_object(panel_path),
        protocol_sha256=digest(protocol_path),
        panel_sha256=digest(panel_path),
    )
    if queue != expected:
        raise QueueItemError("the queue does not match the frozen protocol")
    if (
        authorization.get("schema_version") != AUTHORIZATION_SCHEMA
        or authorization.get("authorized") is not True
        or authorization.get("protocol_sha256") != digest(protocol_path)
        or authorization.get("queue_sha256") != digest(queue_path)
    ):
        raise QueueItemError("no authorization record binds this protocol and queue")
    for field in ("spend_ceiling_usd", "per_attempt_reserve_usd"):
        value = authorization.get(field)
        if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
            raise QueueItemError(f"the authorization record has no positive {field}")
    if authorization["per_attempt_reserve_usd"] > authorization["spend_ceiling_usd"]:
        raise QueueItemError("the per-attempt reserve exceeds the spend ceiling")
    analysis_path = STUDY_ROOT / protocol["measurement"]["analysis_contract"]
    return protocol, queue, read_object(analysis_path)


def validate_committed_authorization(path: Path) -> None:
    """Require the execution authorization to be a clean, tracked study artifact."""
    resolved = path.resolve()
    if resolved.parent != STUDY_ROOT:
        raise QueueItemError("the authorization must be committed in this study directory")
    repository = Path(
        subprocess.run(
            ["git", "-C", str(STUDY_ROOT), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    relative = resolved.relative_to(repository)
    tracked = subprocess.run(
        ["git", "-C", str(repository), "ls-files", "--error-unmatch", str(relative)],
        capture_output=True,
        text=True,
    )
    clean = subprocess.run(
        ["git", "-C", str(repository), "diff", "--quiet", "HEAD", "--", str(relative)]
    )
    if tracked.returncode != 0 or clean.returncode != 0:
        raise QueueItemError("the authorization must be committed and unchanged before execution")


def bind_root(output_root: Path, authorization_sha256: str) -> None:
    """Tie the output root to one authorization so its ledger covers every run."""
    output_root.mkdir(parents=True, exist_ok=True)
    marker = output_root / ROOT_MARKER
    if not marker.exists():
        write_new(marker, {"authorization_sha256": authorization_sha256})
    if read_object(marker).get("authorization_sha256") != authorization_sha256:
        raise QueueItemError("the output root belongs to a different authorization")
    if (output_root / STOP_RECORD).exists():
        raise QueueItemError("the spend ceiling already stopped this queue")


def verify_vero(vero_root: Path, protocol: dict[str, Any]) -> str:
    """The task and the grader both come from the Vero checkout, so pin it every run."""
    pin = read_object(STUDY_ROOT / protocol["source"]["source_pin"])
    load("materialize_probe_task", "materialize_probe_task.py").verify_source(vero_root, pin)
    changed = subprocess.run(
        ["git", "-C", str(vero_root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if changed:
        raise QueueItemError("the Vero checkout has modified or untracked files")
    return pin["commit"]


def leftover_containers(docker: str = "docker") -> list[str]:
    """Sandbox, grader, and holder containers that a killed runner could not remove."""
    found: set[str] = set()
    for selector in ("name=anarres-vero-", "label=anarres.grader", "label=anarres.hold"):
        found.update(
            subprocess.run(
                [docker, "ps", "-aq", "--filter", selector],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()
        )
    return sorted(found)


def is_receipt(path: Path, entry: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    receipt = read_object(path)
    aggregator = load("vero_codex_sol_queue_aggregator", "aggregate_codex_sol_measurements.py")
    if (
        receipt.get("schema_version") != aggregator.RECEIPT_SCHEMA
        or receipt.get("attempt_id") != entry["attempt_id"]
    ):
        raise QueueItemError(f"{path.parent.name} holds a receipt that is not its own")
    return True


def select_entry(queue: dict[str, Any], attempt_id: str, output_root: Path) -> dict[str, Any]:
    """Return the entry when every earlier entry has a receipt and this one has none."""
    matches = [entry for entry in queue["attempts"] if entry["attempt_id"] == attempt_id]
    if len(matches) != 1:
        raise QueueItemError("the attempt ID is absent or duplicated in the frozen queue")
    entry = matches[0]
    for earlier in queue["attempts"][: entry["queue_position"] - 1]:
        if not is_receipt(output_root / earlier["attempt_id"] / "grade-receipt.json", earlier):
            raise QueueItemError(f"queue entry {earlier['attempt_id']} has not finished")
    if is_receipt(output_root / attempt_id / "grade-receipt.json", entry):
        raise QueueItemError("this queue entry already has a receipt")
    return entry


def ledger(attempt_root: Path) -> list[dict[str, Any]]:
    """Every run of one entry, in order; a run that started but never ended is interrupted."""
    runs = []
    started_count = len(list(attempt_root.glob("run-*.started.json")))
    for path in attempt_root.glob("run-*"):
        number = path.name.removeprefix("run-").split(".")[0].split("-")[0]
        if not number.isdigit() or int(number) > started_count:
            raise QueueItemError(f"{attempt_root.name} has a run without a started record")
    for number in range(1, 1 + started_count):
        started = attempt_root / f"run-{number}.started.json"
        finished = attempt_root / f"run-{number}.json"
        if not started.is_file():
            raise QueueItemError(f"{attempt_root.name} has a gap in its run records")
        if finished.is_file():
            runs.append(read_object(finished))
            continue
        record = read_object(started)
        runs.append(
            {
                "schema_version": RUN_SCHEMA,
                "attempt_id": record["attempt_id"],
                "run": number,
                "kind": record["kind"],
                "run_id": None,
                "outcome": "interrupted",
                **dict.fromkeys(USAGE_FIELDS, 0),
                "grading_stage": False,
            }
        )
    return runs


def planning_usd(record: dict[str, Any], analysis: dict[str, Any]) -> float:
    prices = analysis["cost_reporting"]["planning_prices_usd_per_million_tokens"]
    cached = record["cached_input_tokens"]
    return (
        (record["input_tokens"] - cached) * prices["uncached_input"]
        + cached * prices["cached_input"]
        + record["output_tokens"] * prices["output"]
    ) / 1_000_000


def spent_usd(output_root: Path, analysis: dict[str, Any], reserve: float) -> float:
    """Planning cost of every run on the ledger; an interrupted attempt is charged the reserve."""
    total = 0.0
    for attempt_root in sorted(path for path in output_root.iterdir() if path.is_dir()):
        for run in ledger(attempt_root):
            if run["outcome"] == "interrupted":
                total += reserve if run["kind"] == "attempt" else 0.0
            else:
                total += planning_usd(run, analysis)
    return total


def normalized_integrity_errors(result: Any) -> list[str]:
    """Return integrity reasons, including a task tree that defeats bounded collection."""
    errors = list(result.integrity_errors)
    if any(COLLECTION_TIMEOUT in error for error in result.infrastructure_errors):
        errors.append(f"workspace collection failed: {COLLECTION_TIMEOUT}")
    return errors


def outcome(result: Any) -> str:
    if normalized_integrity_errors(result):
        return "integrity_failure"
    if result.infrastructure_errors or result.grade is None:
        return "infrastructure_failure"
    return "scored"


def workspace(probe_root: Path, run_id: str) -> str | None:
    """The collected task workspace, relative to the entry directory, if one exists."""
    run_dir = probe_root / run_id / "run"
    candidates = [run_dir / "source"] if (run_dir / "source").is_dir() else []
    candidates += [path.parent for path in sorted(run_dir.rglob("INSTRUCTION.md"))]
    return None if not candidates else str(candidates[0].relative_to(probe_root.parent))


def run_record(entry: dict[str, Any], run: int, kind: str, result: Any) -> dict[str, Any]:
    errors = result.infrastructure_errors
    integrity_errors = normalized_integrity_errors(result)
    return {
        "schema_version": RUN_SCHEMA,
        "attempt_id": entry["attempt_id"],
        "run": run,
        "kind": kind,
        "run_id": result.attempt_id,
        "outcome": outcome(result),
        **{field: getattr(result, field) for field in USAGE_FIELDS},
        "turns": result.turns,
        "tool_calls": result.tool_calls,
        "agent_wall_seconds": result.wall_seconds,
        "stop_reason": result.stop_reason,
        # Grading failed after the agent finished, so the workspace can be regraded.
        "grading_stage": bool(errors)
        and all(error.startswith("grade: ") for error in errors)
        and not integrity_errors,
        "infrastructure_errors": [error[:ERROR_CHARACTERS] for error in errors],
        "integrity_errors": [error[:ERROR_CHARACTERS] for error in integrity_errors],
        "materialization": result.materialization,
        "sandbox_receipt_sha256": None
        if result.sandbox_receipt is None
        else hashlib.sha256(
            json.dumps(result.sandbox_receipt, sort_keys=True).encode()
        ).hexdigest(),
        "grade": result.grade,
    }


def regrade(
    probe: ModuleType,
    entry: dict[str, Any],
    prior: dict[str, Any],
    attempt_root: Path,
    eval_dir: Path,
    *,
    benchmark_dir: Path,
    vero_root: Path,
    vero_python: str,
    docker_image: str,
) -> Any:
    """Grade the preserved workspace of a run whose grading failed for infrastructure."""
    result = probe.AttemptResult(
        attempt_id=prior["run_id"],
        benchmark_id=entry["benchmark_id"],
        mode=entry["mode"],
        attempt_index=entry["replicate"],
        stop_reason=prior["stop_reason"],
        materialization=prior["materialization"],
    )
    try:
        grade = probe.grade_attempt(
            vero_root,
            vero_python,
            benchmark_dir,
            attempt_root / prior["workspace"],
            entry["mode"],
            eval_dir,
            docker_image=docker_image,
        )
        if grade.get("integrity_violations"):
            result.integrity_errors.append(
                f"grading integrity: {grade['integrity_violations'][:10]}"
            )
        else:
            result.grade = grade
    except Exception as exc:
        result.infrastructure_errors.append(f"grade: {exc}")
    return result


def grade_receipt(
    entry: dict[str, Any],
    runs: list[dict[str, Any]],
    analysis: dict[str, Any],
    authorization_sha256: str,
) -> dict[str, Any]:
    """Convert an entry's ledger into the receipt the frozen aggregate reads."""
    aggregator = load("vero_codex_sol_queue_aggregator", "aggregate_codex_sol_measurements.py")
    final = runs[-1]
    final_outcome = (
        "infrastructure_failure" if final["outcome"] == "interrupted" else final["outcome"]
    )
    scoring = analysis["specification_scoring"]
    per_specification = []

    def reward(status: str) -> int | None:
        # An unknown status stays in the receipt so the aggregate rejects the set.
        try:
            return aggregator.strict_reward(status, scoring)
        except aggregator.AggregateError:
            return None

    if final_outcome == "scored":
        per_specification = [
            {
                "module": spec["module"],
                "specification": spec["spec"],
                "status": spec["status"],
                "strict_reward": reward(spec["status"]),
            }
            for spec in final["grade"]["specs"]
        ]
    receipt: dict[str, Any] = {
        "schema_version": aggregator.RECEIPT_SCHEMA,
        **{
            field: entry[field]
            for field in ("attempt_id", "benchmark_id", "mode", "task_id", "replicate")
        },
        "authorization_sha256": authorization_sha256,
        "outcome": final_outcome,
        "runs": [
            {
                **{field: run[field] for field in ("run", "kind", "run_id", "outcome")},
                **{field: run[field] for field in USAGE_FIELDS},
            }
            for run in runs
        ],
        "integrity_errors": final.get("integrity_errors", []),
        "infrastructure_errors": final.get("infrastructure_errors", []),
        "per_specification": per_specification,
    }
    if final_outcome == "infrastructure_failure":
        return receipt
    # A regrade measures the policy run it graded.
    policy_run = next(run for run in reversed(runs) if run["kind"] == "attempt")
    receipt.update(
        {
            "run_id": policy_run["run_id"],
            "specifications_total": entry["expected_specifications"]
            if final_outcome == "integrity_failure"
            else final["grade"]["total_specs"],
            "materialization": {
                field: policy_run["materialization"][field]
                for field in ("task_tree_sha256", "instruction_sha256")
            },
            **{field: policy_run[field] for field in USAGE_FIELDS},
            **{
                field: policy_run[field]
                for field in ("turns", "tool_calls", "agent_wall_seconds", "stop_reason")
            },
            "model_tokens": policy_run["input_tokens"] + policy_run["output_tokens"],
        }
    )
    return receipt


def run_entry(
    entry: dict[str, Any],
    protocol: dict[str, Any],
    analysis: dict[str, Any],
    authorization: dict[str, Any],
    *,
    authorization_sha256: str,
    output_root: Path,
    vero_root: Path,
    vero_python: str,
    api_key: str,
) -> dict[str, Any]:
    probe = load("run_codex_sol_probe", protocol["starting_policy"]["harness"])
    image = protocol["execution_interface"]["runtime_image_id"]
    directories = {
        record["benchmark_id"]: record["directory"]
        for record in read_object(STUDY_ROOT / protocol["source"]["development_panel"])[
            "repositories"
        ]
    }
    benchmark_dir = vero_root / "benchmarks" / directories[entry["benchmark_id"]]
    bind_root(output_root, authorization_sha256)
    attempt_root = output_root / entry["attempt_id"]
    attempt_root.mkdir(exist_ok=True)
    allowed = protocol["probe_design"]["maximum_infrastructure_retries"] + 1
    while True:
        runs = ledger(attempt_root)
        if len(runs) >= allowed or (
            runs and runs[-1]["outcome"] in ("scored", "integrity_failure")
        ):
            break
        prior = runs[-1] if runs else None
        kind = (
            "regrade" if prior and prior["grading_stage"] and prior.get("workspace") else "attempt"
        )
        if kind == "attempt" and (
            spent_usd(output_root, analysis, authorization["per_attempt_reserve_usd"])
            + authorization["per_attempt_reserve_usd"]
            > authorization["spend_ceiling_usd"]
        ):
            write_new(
                output_root / STOP_RECORD,
                {"attempt_id": entry["attempt_id"], "stopped_at": datetime.now(UTC).isoformat()},
            )
            raise QueueItemError("the spend ceiling leaves no room for another run")
        if leftover_containers():
            raise QueueItemError("remove leftover sandbox and grader containers before a run")
        vero_commit = verify_vero(vero_root, protocol)
        run = len(runs) + 1
        write_new(
            attempt_root / f"run-{run}.started.json",
            {
                "schema_version": STARTED_SCHEMA,
                "attempt_id": entry["attempt_id"],
                "run": run,
                "kind": kind,
                "authorization_sha256": authorization_sha256,
                "vero_commit": vero_commit,
                "vero_python": vero_python,
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
        if kind == "attempt":
            probe_root = attempt_root / f"run-{run}"
            result = probe.run_one_attempt(
                vero_root=vero_root,
                vero_python=vero_python,
                docker_image=image,
                benchmark_id=entry["benchmark_id"],
                benchmark_dir_name=directories[entry["benchmark_id"]],
                mode=entry["mode"],
                attempt_index=entry["replicate"],
                probe_root=probe_root,
                api_key=api_key,
                inference_config_digest=(
                    f"sha256:{protocol['starting_policy']['inference_config_sha256']}"
                ),
            )
            record = run_record(entry, run, kind, result)
            record["workspace"] = workspace(probe_root, result.attempt_id)
        else:
            result = regrade(
                probe,
                entry,
                prior,
                attempt_root,
                attempt_root / f"run-{run}-eval",
                benchmark_dir=benchmark_dir,
                vero_root=vero_root,
                vero_python=vero_python,
                docker_image=image,
            )
            # Regrading calls no model, so it adds no tokens to the ledger.
            record = {
                **run_record(entry, run, kind, result),
                **dict.fromkeys(USAGE_FIELDS, 0),
                "workspace": prior["workspace"],
            }
        write_new(attempt_root / f"run-{run}.json", record)
    receipt = grade_receipt(entry, ledger(attempt_root), analysis, authorization_sha256)
    write_new(attempt_root / "grade-receipt.json", receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--vero-root", type=Path, required=True)
    parser.add_argument("--vero-python", required=True)
    args = parser.parse_args()
    validate_committed_authorization(args.authorization)
    authorization = read_object(args.authorization)
    protocol, queue, analysis = validate_frozen_inputs(
        args.protocol.resolve(), args.queue.resolve(), authorization
    )
    output_root = args.output_root.resolve()
    entry = select_entry(queue, args.attempt_id, output_root)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise QueueItemError("OPENAI_API_KEY is not set")
    receipt = run_entry(
        entry,
        protocol,
        analysis,
        authorization,
        authorization_sha256=digest(args.authorization),
        output_root=output_root,
        vero_root=args.vero_root.resolve(),
        vero_python=args.vero_python,
        api_key=api_key,
    )
    print(f"{entry['attempt_id']}: {receipt['outcome']}")


if __name__ == "__main__":
    main()
