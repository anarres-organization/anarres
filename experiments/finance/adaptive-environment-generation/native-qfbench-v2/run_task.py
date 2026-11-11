#!/usr/bin/env python3
"""Run the v2 task split through the credential-safe v1 harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_RUNNER = ROOT.parent / "native-qfbench-v1" / "run_task.py"

spec = importlib.util.spec_from_file_location("anarres_qfbench_v1_runner", BASE_RUNNER)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load the v1 QF-Bench runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

runner.ROOT = ROOT
runner.SPLIT_PATH = ROOT / "TASK_SPLIT.json"
runner.SOURCE_PATH = ROOT / "SOURCE.json"
runner.AUTHORIZATION_PATH = ROOT / "STAGE_AUTHORIZATION.json"


def frozen_tasks():
    split = runner.json.loads(runner.SPLIT_PATH.read_text())
    indexed = {}
    for partition in ("development", "target", "shared_protected"):
        for row in split[partition]:
            indexed[row["task_id"]] = {**row, "partition": partition}
    return indexed


def authorize_current_stage(task_id):
    row = frozen_tasks().get(task_id)
    if row is None:
        raise RuntimeError(f"Task {task_id!r} is not in the frozen v2 split")
    authorization = runner.json.loads(runner.AUTHORIZATION_PATH.read_text())
    if task_id not in authorization["authorized_task_ids"]:
        raise RuntimeError(f"Task {task_id!r} remains sealed")
    return row


runner.frozen_tasks = frozen_tasks
runner.authorize_current_stage = authorize_current_stage

base_prepare_stage = runner.prepare_stage


def prepare_stage(qfbench_root, task_id, stage, candidate):
    authorization = runner.json.loads(runner.AUTHORIZATION_PATH.read_text())
    candidate_sha256 = None if candidate is None else runner.sha256_file(candidate)
    if candidate_sha256 not in authorization["authorized_candidate_sha256"]:
        raise RuntimeError("candidate condition is not authorized for the current stage")
    return base_prepare_stage(qfbench_root, task_id, stage, candidate)


runner.prepare_stage = prepare_stage

if __name__ == "__main__":
    raise SystemExit(runner.main())
