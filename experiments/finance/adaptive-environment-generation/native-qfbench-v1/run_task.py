#!/usr/bin/env python3
"""Run a frozen QF-Bench task without exposing its verifier to the agent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SPLIT_PATH = ROOT / "TASK_SPLIT.json"
SOURCE_PATH = ROOT / "SOURCE.json"

AGENT_PROMPT = """Complete the quantitative-finance assignment in instruction.md.

Work only inside the current workspace. The task data are in data/. Do not use the
network or inspect files outside this workspace. Hidden verifier files and reference
solutions are intentionally unavailable. If SKILL.md is present, treat it as an
optional task resource. Follow the requested output contract exactly and place every
required deliverable under output/. You may create and run temporary scripts in this
workspace to inspect the provided data and validate your work before finishing.
"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_root(stage: Path) -> Path:
    return stage.parent / f"{stage.name}.anarres"


def run_checked(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, **kwargs)


def frozen_tasks() -> dict[str, dict[str, Any]]:
    specification = json.loads(SPLIT_PATH.read_text())
    indexed: dict[str, dict[str, Any]] = {}
    for row in specification["shared_protected"]:
        indexed[row["task_id"]] = {**row, "partition": "shared_protected"}
    for round_specification in specification["rounds"]:
        for partition in ("development", "target"):
            for row in round_specification[partition]:
                indexed[row["task_id"]] = {
                    **row,
                    "partition": partition,
                    "round": round_specification["round"],
                }
    return indexed


def authorize_current_stage(task_id: str) -> dict[str, Any]:
    row = frozen_tasks().get(task_id)
    if row is None:
        raise RuntimeError(f"Task {task_id!r} is not in the frozen split")
    if row.get("partition") != "development" or row.get("round") != 1:
        raise RuntimeError(
            f"Task {task_id!r} remains sealed until a versioned authorization opens its stage"
        )
    return row


def verify_source(qfbench_root: Path, task_id: str) -> tuple[Path, dict[str, Any]]:
    source = json.loads(SOURCE_PATH.read_text())
    actual_commit = run_checked(
        ["git", "rev-parse", "HEAD"], cwd=qfbench_root, capture_output=True
    ).stdout.strip()
    if actual_commit != source["commit"]:
        raise RuntimeError(f"QF-Bench commit mismatch: {actual_commit} != {source['commit']}")

    row = frozen_tasks().get(task_id)
    if row is None:
        raise RuntimeError(f"Task {task_id!r} is not in the frozen split")
    task_root = qfbench_root / "tasks" / task_id
    checks = {
        "task.toml": row["task_toml_sha256"],
        "instruction.md": row["instruction_sha256"],
    }
    for name, expected in checks.items():
        actual = sha256_file(task_root / name)
        if actual != expected:
            raise RuntimeError(f"{task_id}/{name} hash mismatch: {actual} != {expected}")
    return task_root, row


def prepare_stage(
    qfbench_root: Path,
    task_id: str,
    stage: Path,
    candidate: Path | None,
) -> dict[str, Any]:
    task_root, row = verify_source(qfbench_root, task_id)
    if stage.exists():
        raise RuntimeError(f"Refusing to overwrite existing stage: {stage}")
    stage.mkdir(parents=True)
    shutil.copy2(task_root / "instruction.md", stage / "instruction.md")
    source_data = task_root / "environment" / "data"
    if source_data.is_dir():
        shutil.copytree(source_data, stage / "data")
    else:
        (stage / "data").mkdir()
    (stage / "output").mkdir()

    candidate_sha256 = None
    if candidate is not None:
        if not candidate.is_file():
            raise RuntimeError(f"Candidate is not a file: {candidate}")
        shutil.copy2(candidate, stage / "SKILL.md")
        candidate_sha256 = sha256_file(candidate)

    manifest = {
        "schema_version": 1,
        "task_id": task_id,
        "partition": row["partition"],
        "round": row.get("round"),
        "qfbench_commit": json.loads(SOURCE_PATH.read_text())["commit"],
        "runner_sha256": sha256_file(Path(__file__)),
        "task_toml_sha256": row["task_toml_sha256"],
        "instruction_sha256": row["instruction_sha256"],
        "candidate_sha256": candidate_sha256,
        "source_has_data_directory": source_data.is_dir(),
        "agent_visible_entries": sorted(path.name for path in stage.iterdir()),
    }
    records = record_root(stage)
    records.mkdir()
    (records / "STAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def agent_command(stage: Path, records: Path, model: str | None) -> list[str]:
    command = [
        "codex",
        "exec",
        "--cd",
        str(stage),
        "--approve-for-me",
        "--strict-config",
        "--config",
        "shell_environment_policy.inherit=none",
        "--skip-git-repo-check",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--color",
        "never",
        "--json",
        "--output-last-message",
        str(records / "agent-last-message.txt"),
    ]
    if model:
        command.extend(["--model", model])
    command.append(AGENT_PROMPT)
    return command


def execute_agent(stage: Path, model: str | None, timeout_seconds: int) -> dict[str, Any]:
    records = record_root(stage)
    if not (records / "STAGE_MANIFEST.json").is_file():
        raise RuntimeError("Stage is missing STAGE_MANIFEST.json")

    command = agent_command(stage, records, model)

    start = time.time()
    timed_out = False
    with (
        (records / "agent-events.jsonl").open("w") as stdout_handle,
        (records / "agent-stderr.txt").open("w") as stderr_handle,
    ):
        try:
            completed = subprocess.run(
                command,
                cwd=stage,
                text=True,
                stdout=stdout_handle,
                stderr=stderr_handle,
                timeout=timeout_seconds,
                check=False,
                env={**os.environ, "NO_COLOR": "1"},
            )
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            returncode = 124

    record = {
        "schema_version": 1,
        "command": [part if part != AGENT_PROMPT else "<AGENT_PROMPT>" for part in command],
        "prompt_sha256": hashlib.sha256(AGENT_PROMPT.encode()).hexdigest(),
        "requested_model": model,
        "codex_version": run_checked(["codex", "--version"], capture_output=True).stdout.strip(),
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "returncode": returncode,
        "wall_seconds": round(time.time() - start, 3),
    }
    (records / "AGENT_EXECUTION.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def verify_output(qfbench_root: Path, task_id: str, stage: Path) -> dict[str, Any]:
    task_root, _ = verify_source(qfbench_root, task_id)
    output = stage / "output"
    if not output.is_dir():
        raise RuntimeError(f"Agent output directory is missing: {output}")

    tag = f"anarres-qfbench-{task_id}-{uuid.uuid4().hex[:10]}"
    container = f"{tag}-verify"
    run_checked(["docker", "build", "-t", tag, str(task_root / "environment")])
    run_checked(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            tag,
            "tail",
            "-f",
            "/dev/null",
        ],
        capture_output=True,
    )
    try:
        run_checked(["docker", "exec", container, "mkdir", "-p", "/logs/verifier", "/tests"])
        run_checked(["docker", "cp", f"{output}/.", f"{container}:/app/output/"])
        run_checked(["docker", "cp", f"{task_root / 'tests'}/.", f"{container}:/tests/"])
        start = time.time()
        completed = subprocess.run(
            ["docker", "exec", container, "bash", "/tests/test.sh"],
            text=True,
            capture_output=True,
            check=False,
        )
        wall_seconds = round(time.time() - start, 3)
        reward_dir = record_root(stage) / "verifier"
        reward_dir.mkdir(exist_ok=True)
        (reward_dir / "test-stdout.txt").write_text(completed.stdout)
        (reward_dir / "test-stderr.txt").write_text(completed.stderr)
        reward_copy = subprocess.run(
            [
                "docker",
                "cp",
                f"{container}:/logs/verifier/reward.txt",
                str(reward_dir / "reward.txt"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        reward = None
        if reward_copy.returncode == 0:
            reward = float((reward_dir / "reward.txt").read_text().strip())
        record = {
            "schema_version": 1,
            "task_id": task_id,
            "reward": reward,
            "verifier_returncode": completed.returncode,
            "wall_seconds": wall_seconds,
            "output_files": sorted(
                {
                    str(path.relative_to(output)): sha256_file(path)
                    for path in output.rglob("*")
                    if path.is_file()
                }.items()
            ),
        }
        (record_root(stage) / "VERIFICATION.json").write_text(json.dumps(record, indent=2) + "\n")
        return record
    finally:
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
        subprocess.run(["docker", "rmi", tag], capture_output=True, check=False)


def task_timeout(qfbench_root: Path, task_id: str) -> int:
    task_root, _ = verify_source(qfbench_root, task_id)
    with (task_root / "task.toml").open("rb") as handle:
        return int(tomllib.load(handle)["agent"]["timeout_sec"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qfbench-root", type=Path, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--model")
    parser.add_argument("action", choices=("prepare", "execute", "verify", "run"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    authorize_current_stage(args.task_id)
    if args.action in {"prepare", "run"}:
        prepare_stage(args.qfbench_root, args.task_id, args.stage, args.candidate)
    if args.action in {"execute", "run"}:
        record = execute_agent(
            args.stage, args.model, task_timeout(args.qfbench_root, args.task_id)
        )
        if record["returncode"] != 0:
            print(json.dumps(record, indent=2), file=sys.stderr)
            return record["returncode"]
    if args.action in {"verify", "run"}:
        print(json.dumps(verify_output(args.qfbench_root, args.task_id, args.stage), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
