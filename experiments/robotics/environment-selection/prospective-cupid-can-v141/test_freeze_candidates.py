import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "freeze_candidates", ROOT / "scripts" / "freeze_candidates.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FreezeCandidatesTest(unittest.TestCase):
    def test_builds_disjointly_defined_candidate_rules(self):
        names = [f"demo_{i}" for i in range(12)]
        tiers = {name: ("better", "okay", "worse")[index // 4] for index, name in enumerate(names)}
        candidates = MODULE.build_candidates(
            names=names,
            tiers=tiers,
            merged_ranks=list(range(12)),
            baselines={"random_50": names[::2], "length_50": names[:6]},
            subset_count=6,
            per_tier_count=2,
        )
        self.assertEqual(len(candidates["cupid_50"]), 6)
        balanced = candidates["cupid_tier_balanced_50"]
        self.assertEqual(
            {tier: sum(tiers[x] == tier for x in balanced) for tier in MODULE.TIERS},
            {"better": 2, "okay": 2, "worse": 2},
        )

    def test_rank_reliability_is_one_for_identical_order(self):
        names = [f"demo_{i}" for i in range(6)]
        ranks = MODULE.ordinal_ranks([0, 1, 2, 3, 4, 5], names)
        self.assertAlmostEqual(MODULE.correlation(ranks, ranks), 1.0)
        self.assertEqual(MODULE.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)


if __name__ == "__main__":
    unittest.main()
