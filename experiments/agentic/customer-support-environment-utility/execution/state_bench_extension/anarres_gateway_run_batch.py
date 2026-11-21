"""Run STATE-Bench with one OpenAI-compatible Chat Completions gateway."""

from __future__ import annotations

import json
from pathlib import Path

from clients.anarres_gateway_client import (
    AnarresChatCompletionsClient,
    reset_job_context,
    set_job_context,
)
from state_bench.scripts import run_batch


def _evaluator_client() -> AnarresChatCompletionsClient:
    return AnarresChatCompletionsClient.evaluator_from_env()


_ORIGINAL_RUN_SINGLE = run_batch._run_single


def _run_single_with_attribution(*args, **kwargs):
    task_file = Path(args[0] if args else kwargs["task_file"])
    output_dir = Path(args[3] if len(args) > 3 else kwargs["output_dir"])
    run_name = output_dir.name
    if not run_name.startswith("run") or not run_name[3:].isdigit():
        raise ValueError(f"cannot derive run index from output directory: {output_dir}")
    run_index = int(run_name[3:])
    token = set_job_context(task_id=task_file.stem, run_index=run_index)
    try:
        result = _ORIGINAL_RUN_SINGLE(*args, **kwargs)
        if result.get("status") == "ERR":
            failure_kind = (
                "policy_execution_limit"
                if "exceeded max tool rounds" in str(result.get("error", ""))
                else "runtime_error"
            )
            failure = {
                "schema_version": 1,
                "status": "FAILED_TRAJECTORY",
                "failure_kind": failure_kind,
                "task_id": task_file.stem,
                "run_index": run_index,
                "attempts": result.get("attempts"),
                "error": result.get("error"),
            }
            path = output_dir / f"{task_file.stem}.failure.json"
            path.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    finally:
        reset_job_context(token)


def main() -> None:
    run_batch.build_user_sim_client = _evaluator_client
    run_batch.build_locked_judge_client = _evaluator_client
    run_batch._run_single = _run_single_with_attribution
    run_batch.main()


if __name__ == "__main__":
    main()
