#!/usr/bin/env python3
"""Checks for deterministic Snowball candidate derivation from one probe bank."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "derive_snowball_candidate_measurements", HERE / "derive_snowball_candidate_measurements.py"
)
assert SPEC and SPEC.loader
DERIVE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DERIVE)


def contract() -> dict:
    proposal = json.loads((HERE / "PROBE_BANK_PROPOSAL.json").read_text())
    return {
        "status": "FROZEN_AFTER_PROBES_BEFORE_CANDIDATE_TRAINING",
        "candidate_panel_artifact": "anarres_marin_candidate_panel_proposal_v1",
        "candidate_prompt_groups": proposal["candidate_prompt_groups"],
        "selection_seed": proposal["selection_seed"],
        "source_mapping": proposal["source_mapping"],
    }


def panel() -> dict:
    return json.loads((HERE / "CANDIDATE_PANEL_PROPOSAL.json").read_text())


def probe_bank() -> dict:
    proposal = json.loads((HERE / "PROBE_BANK_PROPOSAL.json").read_text())
    groups = []
    sources = []
    for source_index, (source_id, count) in enumerate(
        proposal["minimum_unique_prompt_groups_by_source"].items()
    ):
        sources.append({"source_id": source_id})
        for index in range(count):
            mass = 1.0 if source_id == "long-loop-smartie-swesmith" else 0.2
            if source_id == "nemotron_if":
                mass = 0.0
            groups.append(
                {
                    "source_id": source_id,
                    "prompt_group_id": f"source-{source_index:02d}-group-{index:03d}",
                    "attempts": 8,
                    "valid_rewards": 8,
                    "admitted_attempts": 8,
                    "infrastructure_invalid_attempts": 0,
                    "verifier_invalid_attempts": 0,
                    "trace_failure_attempts": 0,
                    "admitted_advantage_mass": mass,
                    "generated_tokens": 100,
                }
            )
    return {
        "schema_version": "anarres.snowball-probe-bank.v1",
        "study_id": "snowball-prospective-test",
        "probe_bank_id": "snowball-bank-v1",
        "policy_id": "snowball-starting-policy",
        "policy_revision": "revision-1",
        "sources": sources,
        "groups": groups,
    }


class SnowballCandidateDerivationTest(unittest.TestCase):
    def test_candidates_are_equal_size_deterministic_and_share_fixed_support(self) -> None:
        first = DERIVE.derive(contract(), panel(), probe_bank())
        second = DERIVE.derive(contract(), panel(), probe_bank())
        self.assertEqual(first, second)
        self.assertEqual(len(first["candidates"]), 4)
        for candidate in first["candidates"]:
            self.assertEqual(candidate["coordinates"]["prompt_groups"], 200)
            self.assertEqual(sum(candidate["source_prompt_groups"].values()), 200)

        fixed_sources = set(panel()["fixed_source_shares"])
        memberships = []
        for candidate in first["candidates"]:
            memberships.append(
                {
                    (row["source_id"], row["prompt_group_id"])
                    for row in candidate["prompt_groups"]
                    if row["source_id"] in fixed_sources
                }
            )
        self.assertTrue(all(rows == memberships[0] for rows in memberships[1:]))

        densities = [
            candidate["coordinates"]["usable_signal_density_per_million_generated_tokens"]
            for candidate in first["candidates"]
        ]
        self.assertEqual(densities, sorted(densities, reverse=True))
        self.assertGreater(densities[0], densities[-1])

    def test_insufficient_source_bank_is_rejected(self) -> None:
        bank = probe_bank()
        bank["groups"] = [
            group
            for group in bank["groups"]
            if not (
                group["source_id"] == "long-loop-smartie-swesmith"
                and group["prompt_group_id"].endswith("069")
            )
        ]
        with self.assertRaisesRegex(ValueError, "lacks prompt groups"):
            DERIVE.derive(contract(), panel(), bank)

    def test_unfrozen_derivation_contract_is_rejected(self) -> None:
        draft = contract()
        draft["status"] = "coordination_proposal_not_frozen"
        with self.assertRaisesRegex(ValueError, "not frozen"):
            DERIVE.derive(draft, panel(), probe_bank())

    def test_duplicate_prompt_group_identity_is_rejected(self) -> None:
        bank = probe_bank()
        duplicate = copy.deepcopy(bank["groups"][0])
        duplicate["source_id"] = bank["groups"][-1]["source_id"]
        bank["groups"].append(duplicate)
        with self.assertRaisesRegex(ValueError, "duplicate prompt-group"):
            DERIVE.derive(contract(), panel(), bank)

    def test_malformed_group_is_rejected(self) -> None:
        bank = probe_bank()
        bank["groups"][0]["generated_tokens"] = 0
        with self.assertRaisesRegex(ValueError, "generated tokens"):
            DERIVE.derive(contract(), panel(), bank)


if __name__ == "__main__":
    unittest.main()
