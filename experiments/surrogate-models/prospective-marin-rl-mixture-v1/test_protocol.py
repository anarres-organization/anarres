#!/usr/bin/env python3
"""Checks for the Marin public-reconstruction and prospective-design draft."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "validate_marin_protocol", HERE / "validate_protocol.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class MarinProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = json.loads((HERE / "PROTOCOL.json").read_text())
        self.sources = json.loads((HERE / "SOURCE_AUDIT.json").read_text())
        self.panel = json.loads((HERE / "CANDIDATE_PANEL_PROPOSAL.json").read_text())
        self.inventory = json.loads((HERE / "HISTORICAL_RL_INVENTORY.json").read_text())
        self.ladder = json.loads((HERE / "MODEL_LADDER_AUDIT.json").read_text())

    def test_coordination_draft_cannot_authorize_execution(self) -> None:
        result = VALIDATOR.validate()
        self.assertFalse(result["execution_ready"])
        self.assertFalse(self.protocol["execution_authorized"])
        self.assertFalse(self.protocol["prediction_contract"]["protected_outcomes_opened"])
        self.assertTrue(result["unfrozen_future_fields"])
        self.assertTrue(result["unsatisfied_required_gates"])

    def test_candidate_environment_is_the_only_intervention(self) -> None:
        self.assertEqual(
            self.protocol["scope"]["intervention"], "candidate environment mixture only"
        )
        excluded = set(self.protocol["scope"]["excluded_joint_search"])
        self.assertTrue({"optimizer", "learning_rate", "rollout_group_size"} <= excluded)

    def test_sources_preserve_retrospective_boundary(self) -> None:
        records = {row["id"]: row for row in self.sources["records"]}
        self.assertEqual(records["marin_12201"]["status"], "retrospective_confounded")
        self.assertEqual(records["marin_11337"]["status"], "development_only")
        self.assertFalse(self.sources["conclusion"]["prospective_claim_allowed"])

    def test_model_ladder_does_not_overclaim_rl_scaling(self) -> None:
        rungs = self.ladder["grug_pretraining_ladder"]["rungs"]
        self.assertEqual(
            [row["model_id"] for row in rungs],
            [
                "grug_d768",
                "grug_d1024",
                "grug_d1536",
                "grug_d2048",
                "hero_d6144",
            ],
        )
        conclusion = self.ladder["conclusion"]
        self.assertEqual(conclusion["matched_post_training_scales_available_now"], 2)
        self.assertFalse(conclusion["rl_scaling_law_supported_now"])
        self.assertTrue(conclusion["cross_scale_transfer_test_supported_now"])
        by_id = {row["model_id"]: row for row in rungs}
        self.assertEqual(by_id["grug_d2048"]["training_completion"].split()[0], "stopped")

    def test_historical_inventory_preserves_independent_unit(self) -> None:
        self.assertEqual(self.inventory["independent_unit"], "trained intervention")
        records = {row["record_id"]: row for row in self.inventory["records"]}
        self.assertEqual(
            records["mochi_123_12119"]["surrogate_use"],
            "protected_transfer_outcome",
        )
        self.assertEqual(
            records["snowball_group_size_11594"]["surrogate_use"],
            "negative_methodological_control",
        )
        self.assertEqual(
            records["snowball_closure_rl_10079"]["surrogate_use"],
            "multi_target_development_replay",
        )

    def test_attempt_contract_separates_infrastructure(self) -> None:
        fields = set(self.protocol["measurement_contract"]["required_attempt_fields"])
        self.assertTrue(
            {
                "prompt_group_id",
                "policy_version",
                "sampling_probability",
                "loss_eligible_tokens",
                "reward",
                "verifier_status",
                "infrastructure_status",
            }
            <= fields
        )
        self.assertEqual(
            self.protocol["measurement_contract"]["unavailable_reward_policy"],
            "exclude from scientific reward and report separately",
        )

    def test_candidate_proposal_changes_one_quota_axis(self) -> None:
        fixed = self.panel["fixed_nonagentic_groups"]
        self.assertEqual(sum(fixed.values()), 32)
        allocations = []
        for candidate in self.panel["candidates"]:
            groups = candidate["groups"]
            self.assertEqual(sum(fixed.values()) + sum(groups.values()), 64)
            allocations.append(
                (groups["agentic_software_repair"], groups["nemotron_instruction_following"])
            )
        self.assertEqual(allocations, [(32, 0), (22, 10), (12, 20)])
        self.assertEqual(self.panel["status"], "coordination_proposal_not_frozen")


if __name__ == "__main__":
    unittest.main()
