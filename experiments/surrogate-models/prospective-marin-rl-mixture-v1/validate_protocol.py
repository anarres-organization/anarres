#!/usr/bin/env python3
"""Validate the staged Marin RL-mixture protocol without opening outcomes."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTOCOL = HERE / "PROTOCOL.json"
SOURCES = HERE / "SOURCE_AUDIT.json"

REQUIRED_SOURCES = {
    "marin_10197",
    "marin_10314",
    "marin_11337",
    "marin_11535",
    "marin_11594",
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
    errors: list[str] = []

    if protocol["independent_test_unit"] != "trained intervention":
        errors.append("the independent test unit must remain the trained intervention")
    if protocol["prediction_contract"]["protected_outcomes_opened"]:
        errors.append("protected outcomes cannot be open in a coordination draft")
    if protocol["execution_authorized"]:
        errors.append("execution cannot be authorized before the freeze is complete")

    source_ids = {row["id"] for row in audit["records"]}
    missing_sources = sorted(REQUIRED_SOURCES - source_ids)
    if missing_sources:
        errors.append(f"source audit is missing: {', '.join(missing_sources)}")

    fixed = protocol["fixed_contract"]
    missing_freeze_fields = [field for field in FREEZE_FIELDS if fixed[field] in (None, [], {})]
    if not fixed["candidate_mixtures"]:
        missing_freeze_fields.append("candidate_mixtures")
    if not fixed["replicate_seeds"]:
        missing_freeze_fields.append("replicate_seeds")
    if not fixed["source_artifacts"]:
        missing_freeze_fields.append("source_artifacts")

    prediction = protocol["prediction_contract"]
    if not prediction["capability_targets"]:
        missing_freeze_fields.append("capability_targets")
    if not prediction["localized_regression_endpoints"]:
        missing_freeze_fields.append("localized_regression_endpoints")
    if prediction["prediction_receipt"] is None:
        missing_freeze_fields.append("prediction_receipt")
    if protocol["scoring_contract"]["target_weights"] is None:
        missing_freeze_fields.append("target_weights")

    unsatisfied_gates = [
        row["gate"] for row in protocol["stage_gates"] if row["required"] and not row["satisfied"]
    ]
    ready = not errors and not missing_freeze_fields and not unsatisfied_gates
    if protocol["evidence_tier"] == "coordination_draft" and ready:
        errors.append("a complete freeze must advance to a new immutable protocol version")
        ready = False

    return {
        "artifact": "anarres_marin_rl_mixture_readiness_v0",
        "errors": errors,
        "execution_ready": ready,
        "missing_freeze_fields": sorted(set(missing_freeze_fields)),
        "source_records": len(audit["records"]),
        "unsatisfied_required_gates": unsatisfied_gates,
    }


def main() -> None:
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
