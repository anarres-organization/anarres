#!/usr/bin/env python3
"""Convert Business Bench process attempts into qualification JSONL rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_attempt(path: Path, policy_id: str) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    run_dir = path.parent
    traces = []
    for turn in result.get("turns", []):
        trace_path = run_dir / "turns" / str(turn["n"]) / "out" / "anarres_policy_trace.json"
        if trace_path.is_file():
            traces.append(json.loads(trace_path.read_text(encoding="utf-8")))

    turns = result.get("turns", [])
    infrastructure_valid = (
        result.get("error") is None
        and bool(turns)
        and len(traces) == len(turns)
        and all(turn.get("exit_code") == 0 and not turn.get("timed_out") for turn in turns)
    )
    episode_seeds = {trace.get("episode_seed") for trace in traces}
    if len(episode_seeds) == 1 and None not in episode_seeds:
        rollout_seed = next(iter(episode_seeds))
    else:
        rollout_seed = int(result.get("run", 0))

    return {
        "policy_id": policy_id,
        "workflow": result["task"],
        "scenario_id": f"{result['task']}:seed-{result['seed']}",
        "rollout_seed": rollout_seed,
        "infrastructure_valid": infrastructure_valid,
        "tool_protocol_valid": infrastructure_valid
        and all(trace.get("protocol_valid") is True for trace in traces),
        "reward": 1.0 if infrastructure_valid and result.get("passed") is True else 0.0,
        "material_control_violation": bool(result.get("breach")) if infrastructure_valid else False,
        "generated_tokens": sum(
            int((trace.get("usage") or {}).get("completion_tokens") or 0) for trace in traces
        ),
        "tool_calls": sum(
            len(event.get("tool_results") or [])
            for trace in traces
            for event in trace.get("events") or []
        ),
        "truncated": any(trace.get("truncated") is True for trace in traces),
        "source_result": path.parent.name,
    }


def convert(roots: list[Path], policy_id: str) -> list[dict]:
    result_paths = sorted(path for root in roots for path in root.glob("*/result.json"))
    if not result_paths:
        raise ValueError("no Business Bench result.json files found")
    return [load_attempt(path, policy_id) for path in result_paths]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", type=Path, nargs="+")
    parser.add_argument("--policy-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = convert(args.roots, args.policy_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
