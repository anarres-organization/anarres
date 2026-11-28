#!/usr/bin/env python3
"""Validate the staged Marin RL-mixture protocol without opening outcomes."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "PROTOCOL.json"
SOURCES = HERE / "SOURCE_AUDIT.json"
INVENTORY = HERE / "HISTORICAL_RL_INVENTORY.json"
LADDER = HERE / "MODEL_LADDER_AUDIT.json"

REQUIRED_SOURCES = {
    "marin_6279",
    "marin_7786",
    "marin_8435",
    "marin_8901",
    "marin_9735",
    "marin_10079",
    "marin_10197",
    "marin_10305",
    "marin_10388",
    "marin_10314",
    "marin_11337",
    "marin_11535",
    "marin_11594",
    "marin_11722",
    "marin_11723",
    "marin_11862",
    "marin_11863",
    "marin_12069",
    "marin_12103",
    "marin_12119",
    "marin_12189",
    "marin_12199",
    "marin_12201",
    "marin_12267",
    "marin_12360",
    "marin_12386",
}

FREEZE_FIELDS = (
    "candidate_construction_rule",
    "evaluation_policy_revision",
    "generated_token_budget_per_intervention",
    "optimizer",
    "rollout_contract_revision",
    "sampler",
    "starting_checkpoint",
    "trainer_revision",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def validate() -> dict:
    protocol = load(PROTOCOL)
    audit = load(SOURCES)
    inventory = load(INVENTORY)
    ladder = load(LADDER)
    errors: list[str] = []

    if protocol["independent_test_unit"] != "trained intervention":
        errors.append("the independent test unit must remain the trained intervention")
    if protocol["prediction_contract"]["protected_outcomes_opened"]:
        errors.append("protected outcomes cannot be open in a reconstruction draft")
    if protocol["execution_authorized"]:
        errors.append("execution cannot be authorized before the freeze is complete")

    source_ids = {row["id"] for row in audit["records"]}
    missing_sources = sorted(REQUIRED_SOURCES - source_ids)
    if missing_sources:
        errors.append(f"source audit is missing: {', '.join(missing_sources)}")

    if inventory["independent_unit"] != "trained intervention":
        errors.append("historical inventory must preserve the trained intervention as its unit")
    if ladder["conclusion"]["rl_scaling_law_supported_now"]:
        errors.append("the current two-scale post-training record cannot claim an RL scaling law")
    if not ladder["conclusion"]["cross_scale_transfer_test_supported_now"]:
        errors.append("the Snowball-to-Mochi transfer target must remain explicit")

    fixed = protocol["fixed_contract"]
    unfrozen_future_fields = [field for field in FREEZE_FIELDS if fixed[field] in (None, [], {})]
    if not fixed["candidate_mixtures"]:
        unfrozen_future_fields.append("candidate_mixtures")
    if not fixed["replicate_seeds"]:
        unfrozen_future_fields.append("replicate_seeds")
    if not fixed["source_artifacts"]:
        unfrozen_future_fields.append("source_artifacts")

    prediction = protocol["prediction_contract"]
    if not prediction["capability_targets"]:
        unfrozen_future_fields.append("capability_targets")
    if not prediction["localized_regression_endpoints"]:
        unfrozen_future_fields.append("localized_regression_endpoints")
    if prediction["prediction_receipt"] is None:
        unfrozen_future_fields.append("prediction_receipt")
    if protocol["scoring_contract"]["target_weights"] is None:
        unfrozen_future_fields.append("target_weights")

    unsatisfied_gates = [
        row["gate"] for row in protocol["stage_gates"] if row["required"] and not row["satisfied"]
    ]
    ready = not errors and not unfrozen_future_fields and not unsatisfied_gates
    if protocol["evidence_tier"] == "public_reconstruction_draft" and ready:
        errors.append("a complete freeze must advance to a new immutable protocol version")
        ready = False

    return {
        "artifact": "anarres_marin_rl_mixture_readiness_v0",
        "errors": errors,
        "execution_ready": ready,
        "unfrozen_future_fields": sorted(set(unfrozen_future_fields)),
        "source_records": len(audit["records"]),
        "unsatisfied_required_gates": unsatisfied_gates,
    }


def main() -> None:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
