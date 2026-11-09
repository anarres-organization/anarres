import importlib.util
import sys
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

SCRIPT = Path(__file__).parent / "scripts" / "qualify_measurements.py"
SPEC = importlib.util.spec_from_file_location("qualify_measurements", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MeasurementQualificationTests(unittest.TestCase):
    def test_unique_product_count_gate_is_applied_when_present(self):
        records = [
            {
                "canonical_smiles": f"C{index}",
                "target_reward": float(index + 1),
                "reward_status": "ok",
                "oracle_elapsed_seconds": 1.0,
                "reaction_sequence": ["rxn"],
                "reaction_depth": 1,
                "bemis_murcko_scaffold": f"s{index}",
                "graph_embedding": [float(index), float(index % 2)],
            }
            for index in range(4)
        ]
        manifest = {"view_seed": 1, "attempts": 4}
        summary = MODULE.summarize_view(records, manifest)
        self.assertEqual(summary["unique_canonical_products"], 4)

    def test_effective_rank(self):
        values = np.asarray([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [0.0, -1.0]])
        self.assertAlmostEqual(MODULE.effective_rank(values), 2.0)

    def test_js_divergence_identity(self):
        counts = Counter({"a": 2, "b": 1})
        self.assertEqual(MODULE.js_divergence(counts, counts), 0.0)

    def test_js_divergence_disjoint(self):
        result = MODULE.js_divergence(Counter({"a": 1}), Counter({"b": 1}))
        self.assertAlmostEqual(result, np.log(2.0))

    def test_cosine(self):
        self.assertEqual(MODULE.cosine(np.asarray([1.0, 0.0]), np.asarray([1.0, 0.0])), 1.0)

    def test_identical_complete_views_pass(self):
        contract = {
            "study": "test",
            "selected_target": "Q07820",
            "sampling": {"seeds": [1, 2], "attempts_per_view": 4},
            "per_view_gates": {
                "minimum_returned_valid_fraction": 1.0,
                "minimum_unique_canonical_smiles_fraction": 1.0,
                "minimum_reward_eligible_fraction": 1.0,
                "minimum_oracle_completion_fraction": 1.0,
                "minimum_positive_reward_fraction": 1.0,
                "minimum_reward_p90_minus_p10": 0.5,
                "maximum_median_oracle_seconds": 10.0,
                "maximum_p95_oracle_seconds": 10.0,
            },
            "two_view_gates": {
                "maximum_absolute_returned_valid_fraction_difference": 0.0,
                "maximum_absolute_unique_fraction_difference": 0.0,
                "maximum_absolute_reward_eligible_fraction_difference": 0.0,
                "maximum_absolute_positive_reward_fraction_difference": 0.0,
                "maximum_absolute_median_reward_difference": 0.0,
                "maximum_absolute_reward_spread_difference": 0.0,
                "maximum_absolute_mean_reaction_depth_difference": 0.0,
                "maximum_reaction_family_js_divergence": 0.0,
                "maximum_absolute_scaffold_singleton_fraction_difference": 0.0,
                "minimum_graph_embedding_centroid_cosine_similarity": 0.999999,
                "maximum_relative_graph_embedding_effective_rank_difference": 0.0,
            },
        }
        records = [
            {
                "target_id": "Q07820",
                "canonical_smiles": f"C{index}",
                "target_reward": float(index + 1),
                "reward_status": "ok",
                "oracle_elapsed_seconds": 1.0,
                "reaction_sequence": ["rxn"],
                "reaction_depth": 1,
                "bemis_murcko_scaffold": f"s{index}",
                "graph_embedding": [float(index), float(index % 2)],
            }
            for index in range(4)
        ]
        manifests = [
            {
                "view_seed": seed,
                "target_id": "Q07820",
                "attempts": 4,
                "returned_records": 4,
            }
            for seed in (1, 2)
        ]
        result = MODULE.qualify(contract, [records, records], manifests)
        self.assertEqual(result["qualification"], "pass")


if __name__ == "__main__":
    unittest.main()
