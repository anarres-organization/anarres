#!/usr/bin/env python3
"""Build an outcome-blind OSS Verify development panel grouped by entry point."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from audit_release import audit

NAMESPACE = "anarres-oss-verify-development-panel-v1"


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def rank(project: str, harness: str) -> str:
    return hashlib.sha256(f"{NAMESPACE}\0{project}\0{harness}".encode()).hexdigest()


def select_groups(eligible: list[dict[str, Any]], groups: int) -> list[dict[str, Any]]:
    ordered = sorted(eligible, key=lambda row: (row["rank_sha256"], row["group_id"]))
    selected = []
    selected_ids = set()
    represented_projects = set()
    for row in ordered:
        if row["project"] in represented_projects:
            continue
        selected.append(row)
        selected_ids.add(row["group_id"])
        represented_projects.add(row["project"])
        if len(selected) == groups:
            return selected
    for row in ordered:
        if row["group_id"] in selected_ids:
            continue
        selected.append(row)
        if len(selected) == groups:
            break
    return selected


def build_panel(source: Path, pin: dict[str, Any], groups: int) -> dict[str, Any]:
    if groups < 1:
        raise ValueError("groups must be positive")
    source_audit = audit(source, pin)
    statements = load_tsv(source / "index/statements.tsv")
    proofs = load_tsv(source / "index/proofs.tsv")

    by_entry_point: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for statement in statements:
        project, harness, _ = statement["id"].split("/")
        by_entry_point[(project, harness)].append(statement)

    proved_by_entry_point: dict[tuple[str, str], list[str]] = defaultdict(list)
    for proof in proofs:
        key = (proof["library"], proof["entry_point"])
        proved_by_entry_point[key].append(proof["statement"])

    eligible = []
    for (project, harness), rows in by_entry_point.items():
        open_rows = [row for row in rows if row["status"] == "open"]
        proved = sorted(proved_by_entry_point.get((project, harness), []))
        if not open_rows or not proved:
            continue
        eligible.append(
            {
                "project": project,
                "entry_point": harness,
                "group_id": f"{project}/{harness}",
                "rank_sha256": rank(project, harness),
                "proved_oracles": proved,
                "open_statements": [
                    {
                        "id": row["id"],
                        "kind": row["kind"],
                        "revision": int(row["revision"]),
                        "fingerprint": row["fingerprint"],
                    }
                    for row in sorted(open_rows, key=lambda item: item["id"])
                ],
            }
        )

    selected = select_groups(eligible, groups)
    panel = {
        "schema_version": "anarres.formal-verification-development-panel.v1",
        "status": "development_only_runtime_qualification_pending",
        "source_id": pin["source_id"],
        "source_pin_sha256": source_audit["source_pin_sha256"],
        "selection": {
            "namespace": NAMESPACE,
            "grouping_unit": "library_and_entry_point",
            "eligibility": "at_least_one_proved_oracle_and_one_open_statement",
            "selection_rule": "hash_order_with_one_entry_point_per_library_before_reuse",
            "requested_groups": groups,
            "eligible_groups": len(eligible),
            "selected_groups": len(selected),
        },
        "groups": selected,
    }
    panel["panel_sha256"] = hashlib.sha256(
        json.dumps(panel, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return panel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--groups", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = json.loads(args.pin.read_text(encoding="utf-8"))
    panel = build_panel(args.source, pin, args.groups)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(panel, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"selected {panel['selection']['selected_groups']} of "
        f"{panel['selection']['eligible_groups']} eligible entry points"
    )


if __name__ == "__main__":
    main()
