#!/usr/bin/env python3
"""Validate the reaction-environment selection qualification protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_DEVELOPMENT = {
    "hash_uniform",
    "reward_signal",
    "validity_cost",
    "scaffold_coverage",
    "route_coverage",
    "graph_embedding_coverage",
}
EXPECTED_PROSPECTIVE = {"operational_hybrid", "graph_aware_hybrid"}


def canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate(protocol: dict[str, object], sources: dict[str, object]) -> list[str]:
    errors: list[str] = []
    panel = protocol["candidate_panel"]
    development = {candidate["name"] for candidate in panel["development"]}
    prospective = {candidate["name"] for candidate in panel["prospective"]}
    if development != EXPECTED_DEVELOPMENT:
        errors.append(f"development panel differs: {sorted(development)}")
    if prospective != EXPECTED_PROSPECTIVE:
        errors.append(f"prospective panel differs: {sorted(prospective)}")
    if development & prospective:
        errors.append("development and prospective candidates must be disjoint")

    source = protocol["source"]
    if source["rxnflow_commit"] != sources["rxnflow"]["commit"]:
        errors.append("RxnFlow commit differs from SOURCES.json")
    if source["molgenbench_commit"] != sources["molgenbench"]["commit"]:
        errors.append("MolGenBench commit differs from SOURCES.json")

    intervention = protocol["intervention"]
    if intervention["only_arm_specific_input"] != "experience-bank membership":
        errors.append("experience-bank membership must be the only arm-specific input")
    for key in (
        "common_action_space_required",
        "common_reward_required",
        "common_trainer_required",
        "common_empty_state_before_bank_preload_required",
        "static_replay_bank_required",
    ):
        if not intervention[key]:
            errors.append(f"{key} must remain true")

    if protocol["starting_policy"]["qed_optimizer_or_replay_state_reused"]:
        errors.append("QED optimizer and replay state cannot enter target training")
    if intervention["rxnflow_num_replay_insert"] != 0:
        errors.append("online trajectories cannot replace the frozen replay bank")

    if len(set(protocol["training"]["seeds"])) < 2:
        errors.append("at least two distinct training seeds are required")
    if protocol["training"]["matched_budgets"] < 3:
        errors.append("at least three matched budgets are required")

    boundary = protocol["sealed_boundary"]
    if boundary["training_or_evaluation_outcomes_inspected"]:
        errors.append("outcomes must remain uninspected at this stage")
    if boundary["candidate_training_outcomes_exist"]:
        errors.append("candidate outcomes cannot exist before the freeze")
    if boundary["reference_active_results_opened"]:
        errors.append("reference-active results must remain sealed")
    if protocol["prospective_chronology"]["outcomes_available_at_current_stage"]:
        errors.append("prospective outcomes cannot be available at qualification")
    if not protocol["open_gates"]:
        errors.append("open qualification gates must be explicit")
    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=root / "PROTOCOL.json")
    parser.add_argument("--sources", type=Path, default=root / "SOURCES.json")
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    errors = validate(protocol, sources)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"protocol_sha256={canonical_digest(protocol)}")


if __name__ == "__main__":
    main()
