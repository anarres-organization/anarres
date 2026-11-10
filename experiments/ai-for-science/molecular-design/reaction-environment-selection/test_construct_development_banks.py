import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parent / "scripts" / "construct_development_banks.py"
SPEC = importlib.util.spec_from_file_location("construct_development_banks", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row(index: int, smiles: str | None = None) -> dict:
    return {
        "record_id": f"{index:064x}",
        "canonical_smiles": smiles or f"C{index}",
        "reward_status": "ok",
        "target_reward": float(index),
        "graph_embedding": [float(index), float(index % 3), 1.0],
        "bemis_murcko_scaffold": f"s{index % 4}",
        "ring_systems": [f"r{index % 5}"],
        "route_signature": f"route{index % 2}",
        "reaction_families": [f"family{index % 3}"],
        "reaction_depth": index % 3,
        "generated_action_count": 4 - index % 3,
        "oracle_elapsed_seconds": float(20 - index),
    }


class DevelopmentBankTests(unittest.TestCase):
    def test_eligibility_deduplicates_by_lowest_record_id(self):
        first = row(1, "CC")
        second = row(2, "CC")
        failed = row(0, "CO")
        failed["reward_status"] = "scientific_zero"
        kept = MODULE.eligible_records([second, failed, first])
        self.assertEqual([item["record_id"] for item in kept], [first["record_id"]])

    def test_all_banks_have_unique_requested_membership(self):
        records = [row(index) for index in range(20)]
        banks = MODULE.construct(records, 8)
        self.assertEqual(
            set(banks),
            {
                "hash_uniform",
                "reward_signal",
                "validity_cost",
                "scaffold_coverage",
                "route_coverage",
                "graph_embedding_coverage",
            },
        )
        for members in banks.values():
            self.assertEqual(len(members), 8)
            self.assertEqual(len({item["record_id"] for item in members}), 8)

    def test_normalized_representation_is_finite(self):
        values = MODULE.normalized_representation([row(index) for index in range(10)])
        self.assertTrue(np.isfinite(values).all())
        self.assertEqual(values.shape[0], 10)

    def test_insufficient_pool_fails(self):
        with self.assertRaisesRegex(ValueError, "fewer than bank size"):
            MODULE.construct([row(index) for index in range(3)], 4)


if __name__ == "__main__":
    unittest.main()
