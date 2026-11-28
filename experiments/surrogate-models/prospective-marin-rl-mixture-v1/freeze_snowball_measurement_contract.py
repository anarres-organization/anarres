#!/usr/bin/env python3
"""Freeze a qualified Snowball starting-policy measurement contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

REQUIRED_RUNTIME_CHECKS = {
    "checkpoint_load",
    "tokenizer_roundtrip",
    "generation",
    "reward_routing",
    "partial_trace_retention",
    "infrastructure_separation",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def validate_rollout(rollout: dict, proposal: dict) -> None:
    required = {"revision", "sampler", "group_size", "temperature", "max_new_tokens"}
    if set(rollout) != required:
        raise ValueError("rollout contract fields differ from the freeze schema")
    if not rollout["revision"] or not rollout["sampler"]:
        raise ValueError("rollout revision and sampler must be non-empty")
    if rollout["group_size"] != proposal["attempts_per_prompt_group"]:
        raise ValueError("rollout group size differs from the probe-bank proposal")
    temperature = rollout["temperature"]
    if (
        not isinstance(temperature, int | float)
        or isinstance(temperature, bool)
        or not math.isfinite(temperature)
        or temperature < 0
    ):
        raise ValueError("rollout temperature must be finite and non-negative")
    if not isinstance(rollout["max_new_tokens"], int) or rollout["max_new_tokens"] <= 0:
        raise ValueError("maximum new tokens must be a positive integer")


def freeze(
    spec: dict,
    panel: dict,
    proposal: dict,
    starting_policy: dict,
    runtime: dict,
    source_manifest: dict,
) -> dict:
    if spec.get("status") != "ready_to_freeze":
        raise ValueError("measurement freeze input is not ready")
    if spec.get("candidate_outcomes_opened") is not False:
        raise ValueError("candidate outcomes must remain unopened")
    if panel.get("status") != "coordination_proposal_not_frozen":
        raise ValueError("candidate panel has an unexpected status")
    if proposal.get("status") != "coordination_proposal_not_frozen":
        raise ValueError("probe-bank proposal has an unexpected status")
    if not spec.get("study_id") or not spec.get("probe_bank_id"):
        raise ValueError("study and probe-bank identities must be non-empty")
    if not spec.get("policy_id") or not spec.get("policy_revision"):
        raise ValueError("policy identity and revision must be non-empty")

    policy = starting_policy["starting_policy"]
    if not is_sha256(policy.get("certified_model_manifest_sha256")):
        raise ValueError("starting-policy model manifest is not pinned")
    if policy["certified_model_manifest_sha256"] != spec.get("starting_policy_manifest_sha256"):
        raise ValueError("starting-policy manifest differs from the freeze input")
    if not policy.get("portable_checkpoint_revision"):
        raise ValueError("starting policy lacks a portable checkpoint revision")
    if spec["policy_revision"] != policy["portable_checkpoint_revision"]:
        raise ValueError("policy revision differs from the portable checkpoint revision")
    if not is_sha256(spec.get("checkpoint_sha256")):
        raise ValueError("starting checkpoint content digest is not pinned")
    if not is_sha256(spec.get("tokenizer_sha256")):
        raise ValueError("tokenizer content digest is not pinned")

    rollout = spec["rollout_contract"]
    validate_rollout(rollout, proposal)
    if runtime.get("status") != "complete_before_probes":
        raise ValueError("runtime qualification is incomplete")
    if runtime.get("candidate_outcomes_opened") is not False:
        raise ValueError("runtime qualification crosses the outcome boundary")
    if runtime.get("starting_checkpoint_revision") != policy["portable_checkpoint_revision"]:
        raise ValueError("runtime qualification uses another starting checkpoint")
    if runtime.get("starting_checkpoint_sha256") != spec["checkpoint_sha256"]:
        raise ValueError("runtime qualification uses different checkpoint bytes")
    if runtime.get("rollout_contract_revision") != rollout["revision"]:
        raise ValueError("runtime qualification uses another rollout contract")
    if not isinstance(runtime.get("runtime_revision"), str) or not runtime["runtime_revision"]:
        raise ValueError("runtime qualification lacks a runtime revision")
    if not isinstance(runtime.get("image_digest"), str) or not runtime["image_digest"]:
        raise ValueError("runtime qualification lacks an image digest")
    checks = runtime.get("passed_checks", {})
    if set(checks) != REQUIRED_RUNTIME_CHECKS or not all(checks.values()):
        raise ValueError("runtime qualification has not passed every required check")

    if source_manifest.get("status") != "qualified_before_probes":
        raise ValueError("source manifest is not qualified")
    if source_manifest.get("candidate_outcomes_opened") is not False:
        raise ValueError("source qualification crosses the outcome boundary")
    expected = proposal["minimum_unique_prompt_groups_by_source"]
    records = source_manifest.get("sources", [])
    by_source = {row.get("source_id"): row for row in records}
    if len(by_source) != len(records) or set(by_source) != set(expected):
        raise ValueError("source manifest does not cover the exact proposed source set")
    for source_id, minimum in expected.items():
        row = by_source[source_id]
        for field in ("revision", "license", "verifier_revision"):
            if not isinstance(row.get(field), str) or not row[field]:
                raise ValueError(f"source {source_id} lacks {field}")
        if not is_sha256(row.get("task_pool_sha256")):
            raise ValueError(f"source {source_id} lacks a task-pool digest")
        if row.get("qualification_status") != "passed":
            raise ValueError(f"source {source_id} is not qualified")
        eligible = row.get("eligible_prompt_groups")
        if not isinstance(eligible, int) or isinstance(eligible, bool) or eligible < 0:
            raise ValueError(f"source {source_id} has an invalid eligible prompt-group count")
        if eligible < minimum:
            raise ValueError(f"source {source_id} cannot supply its largest candidate prefix")

    return {
        "artifact": "anarres_snowball_measurement_contract_v1",
        "status": "MEASUREMENT_PROTOCOL_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
        "study_id": spec["study_id"],
        "probe_bank_id": spec["probe_bank_id"],
        "starting_policy": {
            "policy_id": spec["policy_id"],
            "policy_revision": spec["policy_revision"],
            "portable_checkpoint_revision": policy["portable_checkpoint_revision"],
            "certified_model_manifest_sha256": policy["certified_model_manifest_sha256"],
            "checkpoint_sha256": spec["checkpoint_sha256"],
            "tokenizer_sha256": spec["tokenizer_sha256"],
        },
        "probe_contract": {
            **rollout,
            "candidate_prompt_groups": proposal["candidate_prompt_groups"],
            "unique_prompt_groups": proposal["total_unique_prompt_groups"],
            "total_attempts": proposal["total_starting_policy_attempts"],
            "selection_seed": proposal["selection_seed"],
            "source_mapping": proposal["source_mapping"],
        },
        "sources": [
            {
                "source_id": source_id,
                "revision": by_source[source_id]["revision"],
                "license": by_source[source_id]["license"],
                "task_pool_sha256": by_source[source_id]["task_pool_sha256"],
                "verifier_revision": by_source[source_id]["verifier_revision"],
                "eligible_prompt_groups": by_source[source_id]["eligible_prompt_groups"],
                "required_prompt_groups": expected[source_id],
            }
            for source_id in sorted(expected)
        ],
        "runtime_qualification": {
            "revision": runtime["runtime_revision"],
            "image_digest": runtime["image_digest"],
            "passed_checks": checks,
        },
        "candidate_panel_artifact": panel["artifact"],
        "candidate_ids": [row["candidate_id"] for row in panel["candidates"]],
        "aggregation_metadata": {
            "schema_version": "anarres.snowball-probe-bank-metadata.v1",
            "study_id": spec["study_id"],
            "probe_bank_id": spec["probe_bank_id"],
            "policy_id": spec["policy_id"],
            "policy_revision": spec["policy_revision"],
            "group_size": rollout["group_size"],
            "temperature": rollout["temperature"],
            "max_new_tokens": rollout["max_new_tokens"],
            "source_revisions": {
                source_id: by_source[source_id]["revision"] for source_id in sorted(expected)
            },
        },
        "outcome_boundary": {
            "candidate_training_started": False,
            "candidate_outcomes_opened": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--probe-proposal", type=Path, required=True)
    parser.add_argument("--starting-policy", type=Path, required=True)
    parser.add_argument("--runtime-qualification", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FileExistsError(arguments.output)
    result = freeze(
        load(arguments.spec),
        load(arguments.panel),
        load(arguments.probe_proposal),
        load(arguments.starting_policy),
        load(arguments.runtime_qualification),
        load(arguments.source_manifest),
    )
    result["bound_inputs"] = {
        "freeze_spec_sha256": sha256(arguments.spec),
        "candidate_panel_sha256": sha256(arguments.panel),
        "probe_bank_proposal_sha256": sha256(arguments.probe_proposal),
        "starting_policy_record_sha256": sha256(arguments.starting_policy),
        "runtime_qualification_sha256": sha256(arguments.runtime_qualification),
        "source_manifest_sha256": sha256(arguments.source_manifest),
        "freeze_script_sha256": sha256(Path(__file__)),
    }
    arguments.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
