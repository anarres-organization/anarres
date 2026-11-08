import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "freeze_candidates.py"
SPEC = importlib.util.spec_from_file_location("freeze_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CandidateFreezeTest(unittest.TestCase):
    def test_atom_strata_cover_frozen_source_range(self):
        self.assertEqual(MODULE.atom_stratum(2), 0)
        self.assertEqual(MODULE.atom_stratum(30), 3)
        self.assertEqual(MODULE.atom_stratum(306), 7)
        with self.assertRaises(ValueError):
            MODULE.atom_stratum(1)

    def test_largest_remainder_is_exact_and_deterministic(self):
        counts = [707, 1116, 1938, 2055, 1196, 382, 286, 129]
        self.assertEqual(
            MODULE.largest_remainder_quotas(counts, 256), [23, 37, 64, 67, 39, 13, 9, 4]
        )
        self.assertEqual(sum(MODULE.largest_remainder_quotas(counts, 1024)), 1024)

    def test_segment_quotas_reconstruct_nested_budgets(self):
        counts = [707, 1116, 1938, 2055, 1196, 382, 286, 129]
        segments = MODULE.segment_quotas(counts)
        self.assertEqual([sum(segment) for segment in segments], [256, 256, 512])
        cumulative = [sum(values) for values in zip(*segments, strict=True)]
        self.assertEqual(cumulative, MODULE.largest_remainder_quotas(counts, 1024))

    def test_repeatability_audit_accepts_identical_records(self):
        rows = []
        for index in range(7809):
            rows.append(
                {
                    "record_id": f"record-{index}",
                    "singleton_objective_signal": float(index),
                    "embedding": [1.0, float(index % 2)],
                }
            )
        expected = sorted(
            rows,
            key=lambda row: (
                MODULE.hashlib.sha256(f"repeatability-v1|{row['record_id']}".encode()).hexdigest(),
                row["record_id"],
            ),
        )[:128]
        result = MODULE.repeatability_audit(rows, expected)
        self.assertTrue(result["passes"])

    def test_jaccard(self):
        self.assertEqual(MODULE.jaccard({"a", "b"}, {"b", "c"}), 1 / 3)


if __name__ == "__main__":
    unittest.main()
