#!/usr/bin/env python3
"""Validate the customer-support source registry and qualification record."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROLES = {
    "construction_and_primary_evaluation",
    "external_transfer_candidate",
    "voice_extension_candidate",
}
ALLOWED_OUTCOME_USE = {"none", "external only", "no construction use"}


def load_json(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def validate_sources(payload: dict) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError("SOURCES.json must use schema_version 1")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("SOURCES.json must contain a non-empty sources list")
    ids = [source.get("id") for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("source ids must be unique")
    for source in sources:
        required = (
            "id",
            "name",
            "url",
            "revision",
            "license",
            "access",
            "role",
            "status",
            "outcome_use",
        )
        missing = [key for key in required if not source.get(key)]
        if missing:
            raise ValueError(f"{source.get('id', '<unknown>')} lacks {missing}")
        if source["role"] not in ALLOWED_ROLES:
            raise ValueError(f"unsupported role for {source['id']}: {source['role']}")
        if source["outcome_use"] not in ALLOWED_OUTCOME_USE:
            raise ValueError(f"unsafe outcome_use for {source['id']}")
        if source["id"] in {"state_bench", "tau2_bench"} and len(source["revision"]) != 40:
            raise ValueError(f"{source['id']} must use a full Git commit")


def validate_protocol(protocol: dict, sources: dict) -> None:
    if protocol.get("schema_version") != 1:
        raise ValueError("PROTOCOL.json must use schema_version 1")
    source_ids = {source["id"] for source in sources["sources"]}
    if protocol["source"]["primary"] not in source_ids:
        raise ValueError("primary source is absent from SOURCES.json")
    if protocol["status"] != "SOURCE_QUALIFIED__PROSPECTIVE_CONTRACT_NOT_FROZEN":
        raise ValueError("protocol status must preserve the prospective boundary")
    if not protocol["unresolved_before_freeze"]:
        raise ValueError("unresolved freeze requirements must remain explicit")
    if len(protocol["required_baselines"]) < 4:
        raise ValueError("protocol must retain simple decision baselines")


def validate_qualification(qualification: dict, sources: dict, protocol: dict) -> None:
    source = next(item for item in sources["sources"] if item["id"] == qualification["source_id"])
    if qualification["revision"] != source["revision"]:
        raise ValueError("qualification revision differs from source registry")
    if qualification["revision"] != protocol["source"]["revision"]:
        raise ValueError("qualification revision differs from protocol")
    audit = qualification["source_audit"]
    if audit["train_split_count"] + audit["test_split_count"] != audit["active_task_count"]:
        raise ValueError("train and test counts do not cover the task inventory")
    if audit["train_test_overlap"] != 0:
        raise ValueError("train and test identities overlap")
    if not audit["training_trajectories_match_train_split"]:
        raise ValueError("released trajectories do not match the train split")
    hashes = qualification["content_hashes"]
    if not hashes or any(len(value) != 64 for value in hashes.values()):
        raise ValueError("qualification must retain complete SHA-256 hashes")
    if qualification["model_calls_made"] != 0:
        raise ValueError("source qualification must not make model calls")
    if qualification["scientific_outcomes_opened"]:
        raise ValueError("source qualification must not open scientific outcomes")


def validate_scoring(scoring: dict, protocol: dict) -> None:
    if scoring.get("study_id") != protocol["study_id"]:
        raise ValueError("scoring contract belongs to a different study")
    if scoring.get("status") != "SCORING_CONTRACT_FROZEN__HELD_OUT_OUTCOMES_UNOPENED":
        raise ValueError("scoring contract status must preserve the prospective boundary")
    if scoring.get("held_out_outcomes_opened") is not False:
        raise ValueError("scoring contract must precede held-out outcomes")
    if scoring.get("baseline_arm") in scoring.get("candidate_arms", []):
        raise ValueError("baseline arm must remain separate from candidate arms")
    if scoring.get("allocation_decision_set") != "no_learning baseline and all candidate arms":
        raise ValueError("allocation regret must retain the option not to learn")
    if scoring.get("predicted_choice") not in scoring.get("candidate_arms", []):
        raise ValueError("point prediction is not a candidate arm")
    if scoring.get("runs_per_task") != protocol["source"]["official_runs_per_task"]:
        raise ValueError("scoring run count differs from the source protocol")
    if scoring.get("regression", {}).get("material_threshold", 0) >= 0:
        raise ValueError("material regression threshold must be negative")
    if not scoring.get("regression", {}).get("multiplicity_policy"):
        raise ValueError("regression reporting must state its multiplicity policy")


def validate_run_template(template: dict, protocol: dict) -> None:
    if template.get("study_id") != protocol["study_id"]:
        raise ValueError("run-contract template belongs to a different study")
    if template.get("status") != "DRAFT__NOT_EXECUTABLE":
        raise ValueError("checked-in run contract must remain a non-executable template")
    if template.get("starting_agent", {}).get("model_name") is not None:
        raise ValueError("run-contract template must not imply a chosen starting agent")


def validate() -> tuple[dict, dict, dict]:
    sources = load_json("SOURCES.json")
    protocol = load_json("PROTOCOL.json")
    qualification = load_json("SOURCE_QUALIFICATION.json")
    scoring = load_json("SCORING_CONTRACT.json")
    run_template = load_json("RUN_CONTRACT.template.json")
    validate_sources(sources)
    validate_protocol(protocol, sources)
    validate_qualification(qualification, sources, protocol)
    validate_scoring(scoring, protocol)
    validate_run_template(run_template, protocol)
    return sources, protocol, qualification


def main() -> None:
    sources, _, qualification = validate()
    audit = qualification["source_audit"]
    print(
        "customer-support source audit passed: "
        f"{len(sources['sources'])} registered sources, "
        f"{audit['training_trajectory_count']} training trajectories, "
        f"{audit['test_split_count']} held-out tasks, no outcomes opened"
    )


if __name__ == "__main__":
    main()
