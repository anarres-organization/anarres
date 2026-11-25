#!/usr/bin/env python3
"""Extract compact task outcomes from the pinned tau2-bench result files."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

MODELS = {
    "claude-3-7-sonnet": "claude-3-7-sonnet",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
    "o4-mini": "o4-mini",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identify(filename: str) -> tuple[str, str]:
    domain = next(
        domain for domain in ("airline", "retail", "telecom") if f"_{domain}_" in filename
    )
    model = next(
        MODELS[prefix]
        for prefix in sorted(MODELS, key=len, reverse=True)
        if filename.startswith(prefix)
    )
    return domain, model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    study = Path(__file__).resolve().parents[1]
    sources = json.loads((study / "SOURCES.json").read_text())
    results_root = args.checkout / "data/tau2/results/final"
    records = []
    for filename, expected_size, expected_hash in sources["artifacts"]:
        path = results_root / filename
        if path.stat().st_size != expected_size or sha256(path) != expected_hash:
            raise ValueError(f"source identity mismatch: {filename}")
        payload = json.loads(path.read_text())
        outcomes: dict[str, list[int]] = defaultdict(list)
        for simulation in payload["simulations"]:
            reward = simulation["reward_info"]["reward"]
            if reward not in (0, 0.0, 1, 1.0):
                raise ValueError(f"non-binary reward in {filename}: {reward}")
            outcomes[str(simulation["task_id"])].append(int(reward))
        actions = {
            str(task["id"]): len((task.get("evaluation_criteria") or {}).get("actions") or [])
            for task in payload["tasks"]
        }
        if set(outcomes) != set(actions) or any(len(values) != 4 for values in outcomes.values()):
            raise ValueError(f"unexpected task or trial structure: {filename}")
        domain, model = identify(filename)
        records.append(
            {
                "domain": domain,
                "model": model,
                "source_file": filename,
                "tasks": [
                    {
                        "task_id": task_id,
                        "required_action_count": actions[task_id],
                        "rewards": outcomes[task_id],
                    }
                    for task_id in sorted(outcomes)
                ],
            }
        )
    compact = {
        "schema_version": 1,
        "source_revision": sources["revision"],
        "source_manifest_sha256": sha256(study / "SOURCES.json"),
        "records": sorted(records, key=lambda row: (row["domain"], row["model"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"records": len(records), "tasks": sum(len(row["tasks"]) for row in records)},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
