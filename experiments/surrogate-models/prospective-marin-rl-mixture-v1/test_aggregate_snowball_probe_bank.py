#!/usr/bin/env python3
"""Checks for Snowball starting-policy probe-bank aggregation."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "aggregate_snowball_probe_bank", HERE / "aggregate_snowball_probe_bank.py"
)
assert SPEC and SPEC.loader
AGGREGATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AGGREGATE)


def metadata() -> dict:
    return {
        "schema_version": "anarres.snowball-probe-bank-metadata.v1",
        "study_id": "snowball-test",
        "probe_bank_id": "bank-v1",
        "policy_id": "snowball-sft",
        "policy_revision": "revision-1",
        "group_size": 4,
        "temperature": 0.7,
        "max_new_tokens": 1024,
        "source_revisions": {"source-a": "a1", "source-b": "b1"},
    }


def attempt(source: str, group: str, sample: int, reward: float | None) -> dict:
    return {
        "attempt_id": f"{source}-{group}-{sample}",
        "probe_bank_id": "bank-v1",
        "source_id": source,
        "task_id": f"task-{group}",
        "prompt_group_id": group,
        "sample_index": sample,
        "policy_version": "revision-1",
        "sampling_probability": 0.25,
        "generated_tokens": 10,
        "loss_eligible_tokens": 8,
        "reward": reward,
        "verifier_status": "valid",
        "admission_status": "admitted",
        "infrastructure_status": "valid",
        "termination_reason": "completed",
        "tool_call_status": "not_applicable",
        "trace_digest": f"digest-{source}-{group}-{sample}",
    }


def attempts() -> list[dict]:
    return [
        *[
            attempt("source-a", "group-a", sample, reward)
            for sample, reward in enumerate([0, 1, 0, 1])
        ],
        *[attempt("source-b", "group-b", sample, 1) for sample in range(4)],
    ]


class SnowballProbeBankTest(unittest.TestCase):
    def test_frozen_contract_supplies_aggregation_metadata(self) -> None:
        contract = {
            "status": "MEASUREMENT_PROTOCOL_FROZEN__CANDIDATE_OUTCOMES_UNOPENED",
            "outcome_boundary": {
                "candidate_training_started": False,
                "candidate_outcomes_opened": False,
            },
            "aggregation_metadata": metadata(),
        }
        self.assertEqual(AGGREGATE.metadata_from_freeze(contract), metadata())
        contract["outcome_boundary"]["candidate_training_started"] = True
        with self.assertRaisesRegex(ValueError, "outcome boundary"):
            AGGREGATE.metadata_from_freeze(contract)

    def test_aggregates_signal_and_zero_variance_separately(self) -> None:
        result = AGGREGATE.aggregate(metadata(), attempts())
        sources = {row["source_id"]: row for row in result["sources"]}
        source_a = sources["source-a"]["coordinates"]
        source_b = sources["source-b"]["coordinates"]
        self.assertAlmostEqual(source_a["total_admitted_advantage_mass"], 8 / 3)
        self.assertAlmostEqual(
            source_a["usable_signal_density_per_million_generated_tokens"], 1e6 / 15
        )
        self.assertAlmostEqual(source_a["effective_prompt_coverage"], 1.0)
        self.assertEqual(source_b["total_admitted_advantage_mass"], 0.0)
        self.assertEqual(source_b["effective_prompt_coverage"], 0.0)
        self.assertIn("separately frozen reweighting", result["boundary"])

    def test_infrastructure_failure_is_not_reward_zero(self) -> None:
        rows = attempts()
        failed = rows[0]
        failed["infrastructure_status"] = "invalid"
        failed["verifier_status"] = "unavailable"
        failed["reward"] = None
        failed["admission_status"] = "excluded"
        failed["loss_eligible_tokens"] = 0
        result = AGGREGATE.aggregate(metadata(), rows)
        source_a = next(row for row in result["sources"] if row["source_id"] == "source-a")
        self.assertAlmostEqual(source_a["validity"]["infrastructure_invalid_fraction"], 0.25)
        group = next(row for row in result["groups"] if row["source_id"] == "source-a")
        self.assertEqual(group["valid_rewards"], 3)
        self.assertEqual(group["reward_mean"], 2 / 3)

    def test_invalid_attempt_cannot_carry_reward(self) -> None:
        rows = attempts()
        rows[0]["infrastructure_status"] = "invalid"
        rows[0]["admission_status"] = "excluded"
        rows[0]["loss_eligible_tokens"] = 0
        with self.assertRaisesRegex(ValueError, "must not carry"):
            AGGREGATE.aggregate(metadata(), rows)

    def test_incomplete_prompt_group_is_rejected(self) -> None:
        rows = attempts()
        rows.pop(0)
        with self.assertRaisesRegex(ValueError, "frozen sample indices"):
            AGGREGATE.aggregate(metadata(), rows)

    def test_duplicate_attempt_identity_is_rejected(self) -> None:
        rows = attempts()
        duplicate = copy.deepcopy(rows[0])
        duplicate["source_id"] = "source-b"
        duplicate["prompt_group_id"] = "group-b"
        duplicate["task_id"] = "task-group-b"
        duplicate["sample_index"] = 0
        rows.append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate attempt identity"):
            AGGREGATE.aggregate(metadata(), rows)


if __name__ == "__main__":
    unittest.main()
