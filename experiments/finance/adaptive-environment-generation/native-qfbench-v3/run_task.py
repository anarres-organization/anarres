#!/usr/bin/env python3
"""Run v3 through the credential-safe QF-Bench harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "native-qfbench-v1" / "run_task.py"
SHARED = ROOT.parent / "native-qfbench-v2"

spec = importlib.util.spec_from_file_location("anarres_qfbench_v1_runner", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load the QF-Bench runner")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

runner.ROOT = ROOT
runner.SPLIT_PATH = SHARED / "TASK_SPLIT.json"
runner.SOURCE_PATH = SHARED / "SOURCE.json"
runner.AUTHORIZATION_PATH = ROOT / "STAGE_AUTHORIZATION.json"


def frozen_tasks():
    split = runner.json.loads(runner.SPLIT_PATH.read_text())
    return {
        row["task_id"]: {**row, "partition": partition}
        for partition in ("development", "target", "shared_protected")
        for row in split[partition]
    }


def authorize_current_stage(task_id):
    row = frozen_tasks().get(task_id)
    authorization = runner.json.loads(runner.AUTHORIZATION_PATH.read_text())
    if row is None or task_id not in authorization["authorized_task_ids"]:
        raise RuntimeError(f"Task {task_id!r} remains sealed")
    return row


base_prepare_stage = runner.prepare_stage


def prepare_stage(qfbench_root, task_id, stage, candidate):
    if candidate is None:
        raise RuntimeError("v3 development authorizes only the revised candidate")
    authorization = runner.json.loads(runner.AUTHORIZATION_PATH.read_text())
    if runner.sha256_file(candidate) not in authorization["authorized_candidate_sha256"]:
        raise RuntimeError("candidate condition is not authorized")
    return base_prepare_stage(qfbench_root, task_id, stage, candidate)


runner.frozen_tasks = frozen_tasks
runner.authorize_current_stage = authorize_current_stage
runner.prepare_stage = prepare_stage

if __name__ == "__main__":
    raise SystemExit(runner.main())
