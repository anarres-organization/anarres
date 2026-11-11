"""Audit a Harvey LAB source pool without reading candidate outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SCENARIO_SUFFIX = re.compile(r"/scenario-\d+$")
SHA256 = re.compile(r"[0-9a-f]{64}")
INVENTORY_FIELDS = {
    "criteria_count",
    "criterion_source_reference_count",
    "deliverable_count",
    "instruction_characters",
    "outcomes_read",
    "practice_area",
    "shared_document_corpus",
    "task_id",
    "task_sha256",
    "work_type",
}
PANEL_FIELDS = {
    "criteria_count",
    "outcomes_read",
    "panel_id",
    "practice_area_counts",
    "salt",
    "selection",
    "task_count",
    "task_hashes",
    "task_ids",
    "work_type_counts",
}


def family_id(task_id: str) -> str:
    """Keep variants of one scenario family in the same partition."""
    return SCENARIO_SUFFIX.sub("", task_id)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inventory(path: Path) -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or set(row) - INVENTORY_FIELDS:
            raise ValueError(f"unexpected inventory fields at line {line_number}")
        task_id = row["task_id"]
        task_hash = row["task_sha256"]
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"invalid task identity at inventory line {line_number}")
        if not isinstance(task_hash, str) or not SHA256.fullmatch(task_hash):
            raise ValueError(f"invalid task hash at inventory line {line_number}")
        if task_id in tasks:
            raise ValueError(f"duplicate inventory task: {task_id}")
        if row.get("outcomes_read") is not False:
            raise ValueError(f"inventory row is not outcome-blind: {task_id}")
        tasks[task_id] = row
    if not tasks:
        raise ValueError("empty task inventory")
    return tasks


def load_panel(path: Path, inventory: dict[str, dict]) -> set[str]:
    panel = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(panel, dict) or set(panel) - PANEL_FIELDS:
        raise ValueError(f"unexpected panel fields: {path.name}")
    task_ids = panel["task_ids"]
    task_hashes = panel["task_hashes"]
    if panel.get("outcomes_read") is not False:
        raise ValueError(f"panel is not outcome-blind: {path.name}")
    if (
        not isinstance(task_ids, list)
        or any(not isinstance(task_id, str) for task_id in task_ids)
        or len(task_ids) != len(set(task_ids))
        or panel.get("task_count") not in (None, len(task_ids))
    ):
        raise ValueError(f"invalid or duplicate panel tasks: {path.name}")
    if not isinstance(task_hashes, dict):
        raise ValueError(f"invalid panel task hashes: {path.name}")
    if set(task_hashes) != set(task_ids):
        raise ValueError(f"panel task/hash identities differ: {path.name}")
    for task_id in task_ids:
        if task_id not in inventory:
            raise ValueError(f"panel task absent from inventory: {task_id}")
        if inventory[task_id]["task_sha256"] != task_hashes[task_id]:
            raise ValueError(f"panel task hash differs from inventory: {task_id}")
    return set(task_ids)


def screened_pool(
    inventory_path: Path, probe_path: Path, target_path: Path
) -> tuple[list[dict], Counter, int, int, int]:
    """Return only candidate-source rows after validating protected panels."""
    inventory = load_inventory(inventory_path)
    probe = load_panel(probe_path, inventory)
    target = load_panel(target_path, inventory)
    if probe & target:
        raise ValueError("probe and target share exact task identities")

    protected_families = {family_id(task_id) for task_id in probe | target}
    excluded = Counter()
    eligible: list[dict] = []
    for task_id, row in inventory.items():
        if task_id in probe | target:
            excluded["probe_or_target_task"] += 1
        elif family_id(task_id) in protected_families:
            excluded["shared_scenario_family"] += 1
        elif row.get("shared_document_corpus") is True:
            excluded["shared_document_corpus"] += 1
        else:
            eligible.append(row)
    return eligible, excluded, len(inventory), len(probe), len(target)


def audit(inventory_path: Path, probe_path: Path, target_path: Path) -> dict:
    eligible, excluded, inventory_count, probe_count, target_count = screened_pool(
        inventory_path, probe_path, target_path
    )

    members = "\n".join(
        f"{row['task_id']}\t{row['task_sha256']}"
        for row in sorted(eligible, key=lambda item: item["task_id"])
    )
    return {
        "status": "source_pool_audit_only",
        "outcomes_read": False,
        "inputs_sha256": {
            "inventory": digest(inventory_path),
            "probe_panel": digest(probe_path),
            "target_panel": digest(target_path),
        },
        "inventory_tasks": inventory_count,
        "probe_tasks": probe_count,
        "target_tasks": target_count,
        "excluded": dict(sorted(excluded.items())),
        "eligible_tasks": len(eligible),
        "eligible_practice_areas": len({row["practice_area"] for row in eligible}),
        "eligible_work_types": dict(
            sorted(Counter(str(row.get("work_type")) for row in eligible).items())
        ),
        "eligible_membership_sha256": hashlib.sha256(members.encode()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--probe-panel", required=True, type=Path)
    parser.add_argument("--target-panel", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.inventory, args.probe_panel, args.target_panel)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
