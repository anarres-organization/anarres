"""Unit tests for the outcome-blind Square construction rules."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent


def load(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


STATE = load("square_state_bank", ROOT / "scripts/build_state_bank.py")
FREEZE = load("square_freeze_candidates", ROOT / "scripts/freeze_candidates.py")
AGGREGATE = load("square_aggregate_probe", ROOT / "scripts/aggregate_probe_measurements.py")


class SquareProtocolTests(unittest.TestCase):
    def test_strata_cover_all_median_cells(self) -> None:
        features = []
        for x in (-1.0, 1.0):
            for y in (-1.0, 1.0):
                for yaw in (0.0, np.pi / 4.0):
                    features.append([x, y, np.cos(yaw), np.sin(yaw)])
        strata, _ = STATE.assign_strata(np.asarray(features))
        self.assertEqual(set(map(int, strata)), set(range(8)))

    def test_greedy_coverage_respects_tier_quota(self) -> None:
        names = [f"demo_{index}" for index in range(12)]
        tiers = {name: FREEZE.TIERS[index // 4] for index, name in enumerate(names)}
        state_features = np.asarray([[0.0], [1.0], [2.0]])
        demo_features = np.arange(12, dtype=float)[:, None] / 4.0
        distances = FREEZE.pairwise_distance(state_features, demo_features)
        selected = FREEZE.greedy_coverage(
            distances,
            names,
            tiers,
            np.ones(3),
            set(names),
            quota=2,
        )
        self.assertEqual(len(selected), 6)
        self.assertEqual(
            {tier: sum(tiers[name] == tier for name in selected) for tier in FREEZE.TIERS},
            {"better": 2, "okay": 2, "worse": 2},
        )

    def test_membership_hash_is_order_invariant(self) -> None:
        self.assertEqual(
            FREEZE.membership_hash(["demo_2", "demo_1"]),
            FREEZE.membership_hash(["demo_1", "demo_2"]),
        )

    def test_probe_aggregation_counts_state_failures(self) -> None:
        protocol = {
            "study_id": "synthetic",
            "state_bank": {"states": 2, "policy_rollout_replicates_per_state": 2},
            "measurement": {
                "qualification": {
                    "minimum_total_successes": 1,
                    "minimum_total_failures": 1,
                    "minimum_populated_strata": 2,
                }
            },
        }
        blobs = []
        for seed in range(3):
            rows = []
            for state_id in range(2):
                for replicate in range(2):
                    rows.append(
                        {
                            "state_id": state_id,
                            "stratum": state_id,
                            "replicate": replicate,
                            "success": (state_id + replicate + seed) % 2 == 0,
                            "exception": None,
                        }
                    )
            blobs.append(
                {
                    "study_id": "synthetic",
                    "policy_id": "all_data_probe",
                    "checkpoint_sha256": f"{seed:064x}",
                    "records": rows,
                }
            )
        result = AGGREGATE.aggregate(blobs, protocol)
        self.assertTrue(result["qualification_passed"])
        self.assertEqual(result["episodes"], 12)
        self.assertEqual([row["trials"] for row in result["states"]], [6, 6])


if __name__ == "__main__":
    unittest.main()
