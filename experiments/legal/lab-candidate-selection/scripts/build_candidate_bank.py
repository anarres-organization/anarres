"""Build outcome-blind LAB sampling distributions from task metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from audit_pool import audit, load_inventory, load_panel, screened_pool
from document_blobs import screen_document_blobs, screen_exact_titles, verify_task_hashes


def bank(rows: list[dict]) -> dict:
    """Give three practical sampling rules the same eligible task support."""
    rows = sorted(rows, key=lambda row: row["task_id"])
    if len(rows) < 4:
        raise ValueError("at least four eligible tasks are required")
    if len({row["task_id"] for row in rows}) != len(rows):
        raise ValueError("candidate bank contains duplicate tasks")
    areas = Counter(row["practice_area"] for row in rows)
    if len(areas) < 2:
        raise ValueError("area-balanced sampling requires two practice areas")
    criteria = sorted(row["criteria_count"] for row in rows)
    if any(not isinstance(value, int) or value < 0 for value in criteria):
        raise ValueError("criterion counts must be nonnegative integers")
    cutoff = criteria[(3 * (len(criteria) - 1)) // 4]
    high_count = sum(row["criteria_count"] >= cutoff for row in rows)
    low_count = len(rows) - high_count
    if not high_count or not low_count:
        raise ValueError("rubric-dense sampling needs two nonempty strata")

    distributions = {
        "source_proportional": [1 / len(rows) for _ in rows],
        "practice_area_balanced": [1 / (len(areas) * areas[row["practice_area"]]) for row in rows],
        "rubric_dense": [
            0.5 / (high_count if row["criteria_count"] >= cutoff else low_count) for row in rows
        ],
    }
    for name, weights in distributions.items():
        if any(not math.isfinite(weight) or weight <= 0 for weight in weights):
            raise ValueError(f"nonpositive or nonfinite candidate weight: {name}")
        if not math.isclose(sum(weights), 1, rel_tol=0, abs_tol=1e-12):
            raise ValueError(f"candidate weights do not sum to one: {name}")

    names = list(distributions)
    distances = {
        f"{left}__{right}": 0.5
        * sum(abs(a - b) for a, b in zip(distributions[left], distributions[right], strict=True))
        for i, left in enumerate(names)
        for right in names[i + 1 :]
    }
    return {
        "status": "metadata_candidate_bank_preflight",
        "outcomes_read": False,
        "task_count": len(rows),
        "task_hashes": {row["task_id"]: row["task_sha256"] for row in rows},
        "practice_area_count": len(areas),
        "rubric_dense_cutoff": cutoff,
        "rubric_dense_high_count": high_count,
        "total_variation": distances,
        "candidates": {
            name: {
                "effective_task_count": 1 / sum(weight * weight for weight in weights),
                "weights": {
                    row["task_id"]: weight for row, weight in zip(rows, weights, strict=True)
                },
            }
            for name, weights in distributions.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--probe-panel", required=True, type=Path)
    parser.add_argument("--target-panel", required=True, type=Path)
    parser.add_argument("--source-repo", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    source_audit = audit(args.inventory, args.probe_panel, args.target_panel)
    rows, _, _, _, _ = screened_pool(args.inventory, args.probe_panel, args.target_panel)
    inventory = load_inventory(args.inventory)
    verified_task_count = verify_task_hashes(
        args.source_repo,
        {task_id: row["task_sha256"] for task_id, row in inventory.items()},
    )
    probe = load_panel(args.probe_panel, inventory)
    target = load_panel(args.target_panel, inventory)
    rows, document_audit = screen_document_blobs(args.source_repo, rows, probe, target)
    rows, title_audit = screen_exact_titles(args.source_repo, rows, probe, target)
    result = bank(rows)
    result["source_audit"] = source_audit
    result["document_audit"] = document_audit
    result["title_audit"] = title_audit
    result["verified_source_task_hashes"] = verified_task_count
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "output_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                "task_count": result["task_count"],
                "candidate_ids": list(result["candidates"]),
                "total_variation": result["total_variation"],
                "document_audit": document_audit,
                "title_audit": title_audit,
                "verified_source_task_hashes": verified_task_count,
                "outcomes_read": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
