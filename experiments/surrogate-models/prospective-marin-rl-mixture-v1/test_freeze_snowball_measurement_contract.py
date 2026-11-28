#!/usr/bin/env python3
"""Checks for the Snowball measurement freeze gate."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "freeze_snowball_measurement_contract", HERE / "freeze_snowball_measurement_contract.py"
)
assert SPEC and SPEC.loader
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)
HEX = "a" * 64


def inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    panel = json.loads((HERE / "CANDIDATE_PANEL_PROPOSAL.json").read_text())
    proposal = json.loads((HERE / "PROBE_BANK_PROPOSAL.json").read_text())
    starting = json.loads((HERE / "SNOWBALL_EXP5_INTERVENTION.json").read_text())
    starting["starting_policy"]["portable_checkpoint_revision"] = "checkpoint-revision-1"
    spec = {
        "status": "ready_to_freeze",
        "candidate_outcomes_opened": False,
        "study_id": "snowball-prospective-v1",
        "probe_bank_id": "snowball-bank-v1",
        "policy_id": "snowball-exp5-sft527",
        "policy_revision": "checkpoint-revision-1",
        "starting_policy_manifest_sha256": starting["starting_policy"][
            "certified_model_manifest_sha256"
        ],
        "checkpoint_sha256": HEX,
        "tokenizer_sha256": "b" * 64,
        "rollout_contract": {
            "revision": "rollout-v1",
            "sampler": "temperature-categorical",
            "group_size": 8,
            "temperature": 0.7,
            "max_new_tokens": 32768,
        },
    }
    runtime = {
        "status": "complete_before_probes",
        "candidate_outcomes_opened": False,
        "starting_checkpoint_revision": "checkpoint-revision-1",
        "starting_checkpoint_sha256": HEX,
        "rollout_contract_revision": "rollout-v1",
        "runtime_revision": "runtime-1",
        "image_digest": "sha256:" + "c" * 64,
        "passed_checks": {name: True for name in FREEZE.REQUIRED_RUNTIME_CHECKS},
    }
    source_manifest = {
        "status": "qualified_before_probes",
        "candidate_outcomes_opened": False,
        "sources": [
            {
                "source_id": source_id,
                "revision": f"revision-{index}",
                "license": "Apache-2.0",
                "task_pool_sha256": f"{index + 1:064x}",
                "verifier_revision": f"verifier-{index}",
                "qualification_status": "passed",
                "eligible_prompt_groups": count,
            }
            for index, (source_id, count) in enumerate(
                proposal["minimum_unique_prompt_groups_by_source"].items()
            )
        ],
    }
    return spec, panel, proposal, starting, runtime, source_manifest


class SnowballMeasurementFreezeTest(unittest.TestCase):
    def test_complete_inputs_freeze_without_opening_outcomes(self) -> None:
        result = FREEZE.freeze(*inputs())
        self.assertEqual(
            result["status"], "MEASUREMENT_PROTOCOL_FROZEN__CANDIDATE_OUTCOMES_UNOPENED"
        )
        self.assertEqual(result["probe_contract"]["unique_prompt_groups"], 245)
        self.assertEqual(result["probe_contract"]["total_attempts"], 1960)
        self.assertEqual(len(result["sources"]), 11)
        self.assertFalse(any(result["outcome_boundary"].values()))
        self.assertEqual(result["aggregation_metadata"]["group_size"], 8)

    def test_current_public_starting_record_cannot_freeze_execution(self) -> None:
        values = list(inputs())
        values[3]["starting_policy"]["portable_checkpoint_revision"] = None
        with self.assertRaisesRegex(ValueError, "portable checkpoint"):
            FREEZE.freeze(*values)

    def test_incomplete_runtime_is_rejected(self) -> None:
        values = list(inputs())
        values[4]["passed_checks"]["partial_trace_retention"] = False
        with self.assertRaisesRegex(ValueError, "every required check"):
            FREEZE.freeze(*values)

    def test_source_shortage_is_rejected(self) -> None:
        values = list(inputs())
        values[5]["sources"][0]["eligible_prompt_groups"] -= 1
        with self.assertRaisesRegex(ValueError, "largest candidate prefix"):
            FREEZE.freeze(*values)

    def test_opened_outcomes_are_rejected(self) -> None:
        values = list(inputs())
        values[0] = copy.deepcopy(values[0])
        values[0]["candidate_outcomes_opened"] = True
        with self.assertRaisesRegex(ValueError, "must remain unopened"):
            FREEZE.freeze(*values)


if __name__ == "__main__":
    unittest.main()
