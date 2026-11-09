#!/usr/bin/env python3
"""Validate and hash the frozen prospective robotics protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def validate(protocol: dict) -> None:
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate ids must be unique")
    if protocol["decision"]["point_prediction_if_gate_passes"] not in candidate_ids:
        raise ValueError("point prediction must name a candidate")
    if set(protocol["decision"]["primary_comparators"]) - set(candidate_ids):
        raise ValueError("all comparators must name candidates")
    seeds = protocol["training"]["seeds"]
    if len(seeds) != len(set(seeds)):
        raise ValueError("training seeds must be unique")
    expected_runs = len(candidate_ids) * len(seeds)
    if protocol["release_gate"]["expected_candidate_runs"] != expected_runs:
        raise ValueError("expected run count does not match candidates x seeds")
    expected_episodes = expected_runs * protocol["evaluation"]["rollouts_per_policy"]
    if protocol["release_gate"]["expected_evaluation_episodes"] != expected_episodes:
        raise ValueError("expected episode count does not match the evaluation grid")
    if not protocol["decision"]["no_outcome_driven_revision"]:
        raise ValueError("prospective contract must prohibit outcome-driven revision")


def main() -> None:
    protocol = json.loads((ROOT / "PROTOCOL.json").read_text())
    sources = json.loads((ROOT / "SOURCES.json").read_text())
    validate(protocol)
    freeze = {
        "protocol_sha256": hashlib.sha256(canonical_bytes(protocol)).hexdigest(),
        "sources_sha256": hashlib.sha256(canonical_bytes(sources)).hexdigest(),
    }
    freeze["freeze_sha256"] = hashlib.sha256(canonical_bytes(freeze)).hexdigest()
    frozen_path = ROOT / "FREEZE.json"
    if frozen_path.exists() and json.loads(frozen_path.read_text()) != freeze:
        raise ValueError("serialized freeze digest does not match protocol and sources")
    print(json.dumps(freeze, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
