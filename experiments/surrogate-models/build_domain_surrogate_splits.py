#!/usr/bin/env python3
"""Freeze grouped replay suites for the domain-centered surrogate corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RECORDS = HERE / "DOMAIN_SURROGATE_RECORDS.jsonl"
INVENTORY = HERE / "DOMAIN_SURROGATE_INVENTORY.json"
DEFAULT_OUTPUT = HERE / "DOMAIN_SURROGATE_SPLITS.json"

SUITES = (
    {
        "suite_id": "controlled_leave_one_study_out",
        "claim": "transfer among unseen controlled training studies in the priority domains",
        "filters": {"evidence_level": "seed_level_intervention"},
        "group": "study_id",
        "status": "primary_controlled",
    },
    {
        "suite_id": "coding_leave_one_decision_out",
        "claim": "transfer to an unseen agentic-coding training decision",
        "filters": {"domain": "agentic_coding"},
        "group": "study_id",
        "status": "primary_retrospective_bridge",
    },
    {
        "suite_id": "materials_leave_one_study_out",
        "claim": "transfer to an unseen materials-science study",
        "filters": {"domain": "materials_science"},
        "group": "study_id",
        "status": "primary_retrospective_bridge",
    },
    {
        "suite_id": "finance_leave_one_study_out",
        "claim": "transfer to an unseen finance post-training study",
        "filters": {"domain": "finance"},
        "group": "study_id",
        "status": "primary_retrospective_bridge",
    },
    {
        "suite_id": "leave_one_domain_out",
        "claim": "transfer to an unseen domain",
        "filters": {},
        "group": "domain",
        "status": "exploratory_due_to_domain_imbalance",
    },
)


def digest_ids(records: list[dict[str, Any]]) -> str:
    payload = "".join(
        f"{row['record_id']}\n" for row in sorted(records, key=lambda x: x["record_id"])
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(record[key] == value for key, value in filters.items())


def build() -> dict[str, Any]:
    records = [json.loads(line) for line in RECORDS.read_text().splitlines()]
    inventory = json.loads(INVENTORY.read_text())
    if len(records) != inventory["records_artifact"]["records"]:
        raise ValueError("domain-surrogate record count does not match inventory")
    if hashlib.sha256(RECORDS.read_bytes()).hexdigest() != inventory["records_artifact"]["sha256"]:
        raise ValueError("domain-surrogate record digest does not match inventory")
    suites = []
    for specification in SUITES:
        selected = [record for record in records if matches(record, specification["filters"])]
        groups: dict[str, list[dict[str, Any]]] = {}
        for record in selected:
            groups.setdefault(str(record[specification["group"]]), []).append(record)
        if len(groups) < 2:
            raise ValueError(f"suite {specification['suite_id']} has fewer than two groups")
        folds = []
        for group, test in sorted(groups.items()):
            test_ids = {record["record_id"] for record in test}
            train = [record for record in selected if record["record_id"] not in test_ids]
            test_panels = {(record["source_id"], record["panel_id"]) for record in test}
            train_panels = {(record["source_id"], record["panel_id"]) for record in train}
            if test_panels & train_panels:
                raise ValueError(f"panel crosses fold {specification['suite_id']}:{group}")
            folds.append(
                {
                    "fold_id": f"holdout:{group}",
                    "test_selector": {
                        "field": specification["group"],
                        "value": group,
                    },
                    "train_records": len(train),
                    "test_records": len(test),
                    "train_record_ids_sha256": digest_ids(train),
                    "test_record_ids_sha256": digest_ids(test),
                }
            )
        suites.append(
            {
                **specification,
                "records": len(selected),
                "panels": len({(row["source_id"], row["panel_id"]) for row in selected}),
                "groups": len(groups),
                "record_ids_sha256": digest_ids(selected),
                "folds": folds,
            }
        )
    return {
        "artifact": "anarres_domain_surrogate_splits_v1",
        "status": "frozen retrospective development suites; not a prospective test",
        "records_sha256": hashlib.sha256(RECORDS.read_bytes()).hexdigest(),
        "rules": {
            "selection": "all model and retrieval choices occur inside each training fold",
            "nesting": (
                "endpoints, tasks, targets, strata, checkpoints, and seeds stay with their "
                "study or decision group"
            ),
            "outcomes": "rank and score candidates only within their native panel",
            "mathematics": (
                "excluded from headline suites; retained in the first replay as a "
                "conformance fixture"
            ),
        },
        "suites": suites,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if args.output.read_text() != rendered:
            raise SystemExit("stale domain-surrogate split freeze")
        return
    args.output.write_text(rendered)


if __name__ == "__main__":
    main()
