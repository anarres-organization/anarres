#!/usr/bin/env python3
"""Recompute G=1 policy pass@1 after excluding a fixed prompt-id list."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--exclude", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    excluded = {
        line.strip() for line in Path(args.exclude).read_text().splitlines() if line.strip()
    }
    by_policy: dict[str, list[tuple[str, float]]] = defaultdict(list)
    source_roots = []
    for root_text in args.root:
        root = Path(root_text)
        source_roots.append(str(root))
        for integrity_path in sorted((root / "results").glob("g1_*/integrity.json")):
            task = integrity_path.parent.name
            match = re.fullmatch(r"g1_(.+)_shard[01]", task)
            if not match:
                continue
            policy = match.group(1)
            integrity = json.loads(integrity_path.read_text())
            evaluation = json.loads(
                (integrity_path.parent / "evaluation_data.json").read_text()
            )["evaluation_data"]
            rows = integrity["rows"]
            if len(rows) != len(evaluation):
                raise RuntimeError(f"row mismatch: {task}")
            for identity, sample in zip(rows, evaluation):
                by_policy[policy].append((identity["prompt_id"], float(sample["reward"])))

    summaries = []
    for policy, rows in sorted(by_policy.items()):
        kept = [reward for prompt_id, reward in rows if prompt_id not in excluded]
        full = [reward for _, reward in rows]
        if len(full) != 1000 or len(kept) != 1000 - len(excluded):
            raise RuntimeError(f"unexpected counts for {policy}: {len(full)}, {len(kept)}")
        summaries.append({
            "policy": policy,
            "n_full": len(full),
            "n_restricted": len(kept),
            "pass1_full": sum(full) / len(full),
            "pass1_restricted": sum(kept) / len(kept),
            "delta_pp": 100 * (sum(kept) / len(kept) - sum(full) / len(full)),
        })
    payload = {
        "excluded_prompt_ids": sorted(excluded),
        "source_roots": source_roots,
        "policy_count": len(summaries),
        "policies": summaries,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({
        "policy_count": len(summaries),
        "maximum_absolute_delta_pp": max(abs(row["delta_pp"]) for row in summaries),
    }, indent=2))


if __name__ == "__main__":
    main()
