#!/usr/bin/env python3
"""Validate the finance source registry and source-preflight record."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROLES = {
    "construction_candidate",
    "external_mechanism_check",
    "external_artifact_evaluation",
    "external_research_evaluation",
    "external_accounting_check",
    "external_design_target",
    "post_trade_representation_candidate",
    "external_reconciliation_design_target",
    "domain_priority_evidence",
}


def load_json(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def validate_sources(payload: dict) -> None:
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("SOURCES.json must contain a non-empty sources list")
    ids = [source.get("id") for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("source ids must be unique")
    for source in sources:
        missing = [
            key
            for key in ("id", "name", "url", "license", "access", "role", "status", "outcome_use")
            if not source.get(key)
        ]
        if missing:
            raise ValueError(f"{source.get('id', '<unknown>')} lacks {missing}")
        if source["role"] not in ALLOWED_ROLES:
            raise ValueError(f"unsupported role for {source['id']}: {source['role']}")
        if source["role"] == "construction_candidate" and not source.get("revision"):
            raise ValueError("a construction source requires an immutable revision")
        if source["role"] != "construction_candidate" and source["outcome_use"] not in {
            "external only",
            "no construction use",
            "none",
        }:
            raise ValueError(f"external source {source['id']} has unsafe outcome_use")


def validate_preflight(preflight: dict, sources: dict) -> None:
    source_ids = {source["id"] for source in sources["sources"]}
    if preflight["source_id"] not in source_ids:
        raise ValueError("preflight source is absent from SOURCES.json")
    expected = len(preflight["workflows"]) * len(preflight["seeds"])
    if preflight["workflow_seed_trials"] != expected:
        raise ValueError("workflow_seed_trials does not match workflows x seeds")
    if preflight["passed_trials"] + preflight["failed_trials"] != expected:
        raise ValueError("preflight pass/fail counts do not cover every trial")
    if preflight["scientific_outcomes_opened"]:
        raise ValueError("source preflight must not contain scientific outcomes")


def main() -> None:
    sources = load_json("SOURCES.json")
    preflight = load_json("PREFLIGHT.json")
    validate_sources(sources)
    validate_preflight(preflight, sources)
    print(
        "finance source audit passed: "
        f"{len(sources['sources'])} sources, "
        f"{preflight['passed_trials']}/{preflight['workflow_seed_trials']} "
        "generator trials passed"
    )


if __name__ == "__main__":
    main()
