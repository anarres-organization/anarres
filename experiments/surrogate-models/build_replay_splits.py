#!/usr/bin/env python3
"""Freeze grouped replay suites over the released intervention corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CORPUS_MANIFEST = HERE / "CORPUS_INVENTORY.json"
CORPUS_RECORDS = HERE / "CORPUS_RECORDS.jsonl"
DEFAULT_OUTPUT = HERE / "REPLAY_SPLITS.json"

SUITES = (
    {
        "suite_id": "seed_level_leave_one_study_out",
        "claim": "transfer to an unseen controlled intervention study",
        "status": "primary",
        "filters": {"evidence_level": "seed_level_intervention"},
        "group_field": "study_id",
    },
    {
        "suite_id": "materials_leave_one_publication_out",
        "claim": "transfer to an unseen materials-science publication",
        "status": "primary_retrospective_bridge",
        "filters": {
            "domain": "materials_science",
            "evidence_level": "published_candidate_arm_aggregate",
        },
        "group_field": "study_id",
    },
    {
        "suite_id": "finance_leave_one_study_out",
        "claim": "transfer to an unseen finance post-training study",
        "status": "primary_retrospective_bridge",
        "filters": {
            "domain": "finance",
            "evidence_level": "published_candidate_arm_aggregate",
        },
        "group_field": "study_id",
    },
    {
        "suite_id": "leave_one_domain_out",
        "claim": "transfer to an unseen domain",
        "status": "exploratory_due_to_domain_imbalance",
        "filters": {},
        "group_field": "domain",
    },
    {
        "suite_id": "mathematics_leave_one_scale_out",
        "claim": "scale transfer under one fixed trainer",
        "status": "conformance_fixture",
        "filters": {"source_id": "mathematics_environment_utility"},
        "group_field": "grouping.scale",
    },
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def nested(record: dict[str, Any], field: str) -> Any:
    value: Any = record
    for part in field.split("."):
        value = value[part]
    return value


def matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(nested(record, field) == expected for field, expected in filters.items())


def record_set_digest(records: list[dict[str, Any]]) -> str:
    payload = "".join(
        f"{row['record_id']}\n" for row in sorted(records, key=lambda row: row["record_id"])
    )
    return sha256_bytes(payload.encode())


def load_records() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CORPUS_RECORDS.read_text().splitlines()]


def build_splits() -> dict[str, Any]:
    manifest = json.loads(CORPUS_MANIFEST.read_text())
    records = load_records()
    if len(records) != manifest["records_artifact"]["records"]:
        raise ValueError("record count does not match the corpus manifest")
    if sha256_bytes(CORPUS_RECORDS.read_bytes()) != manifest["records_artifact"]["sha256"]:
        raise ValueError("record digest does not match the corpus manifest")

    suites = []
    for specification in SUITES:
        selected = [row for row in records if matches(row, specification["filters"])]
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in selected:
            group = str(nested(row, specification["group_field"]))
            groups.setdefault(group, []).append(row)
        if len(groups) < 2:
            raise ValueError(f"suite {specification['suite_id']} has fewer than two groups")

        folds = []
        for group, test_records in sorted(groups.items()):
            test_ids = {row["record_id"] for row in test_records}
            train_records = [row for row in selected if row["record_id"] not in test_ids]
            test_panels = {(row["source_id"], row["panel_id"]) for row in test_records}
            train_panels = {(row["source_id"], row["panel_id"]) for row in train_records}
            if test_panels & train_panels:
                raise ValueError(f"panel lineage crosses fold {specification['suite_id']}:{group}")
            folds.append(
                {
                    "fold_id": f"holdout:{group}",
                    "test_selector": {
                        "field": specification["group_field"],
                        "value": group,
                    },
                    "train_records": len(train_records),
                    "test_records": len(test_records),
                    "train_panels": len(train_panels),
                    "test_panels": len(test_panels),
                    "train_record_ids_sha256": record_set_digest(train_records),
                    "test_record_ids_sha256": record_set_digest(test_records),
                }
            )

        suites.append(
            {
                **specification,
                "records": len(selected),
                "panels": len({(row["source_id"], row["panel_id"]) for row in selected}),
                "groups": len(groups),
                "records_by_domain": dict(
                    sorted(Counter(row["domain"] for row in selected).items())
                ),
                "record_ids_sha256": record_set_digest(selected),
                "folds": folds,
            }
        )

    return {
        "artifact": "anarres_surrogate_replay_splits_v1",
        "status": "frozen retrospective replay suites; no model scores",
        "corpus": {
            "manifest": CORPUS_MANIFEST.name,
            "manifest_sha256": sha256_bytes(CORPUS_MANIFEST.read_bytes()),
            "records": CORPUS_RECORDS.name,
            "records_sha256": sha256_bytes(CORPUS_RECORDS.read_bytes()),
        },
        "rules": {
            "primary_split": "complete study or publication holdout",
            "nested_records": (
                "seeds, checkpoints, tasks, targets, traces, and evaluations stay with "
                "their candidate lineage"
            ),
            "model_selection": "nested inside each training fold",
            "outcome_scale": "native outcomes remain panel-local",
            "random_row_split": "prohibited for primary results",
            "chronological_suite": ("deferred until record-level availability times are released"),
        },
        "suites": suites,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_splits(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            raise SystemExit(f"stale replay split freeze: {args.output}")
        return
    args.output.write_text(rendered)


if __name__ == "__main__":
    main()
