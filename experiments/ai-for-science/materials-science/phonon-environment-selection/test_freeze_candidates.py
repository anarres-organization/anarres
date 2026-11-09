import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "freeze_candidates.py"
SPEC = importlib.util.spec_from_file_location("freeze_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class CandidateFreezeTest(unittest.TestCase):
    def test_canonical_digest_survives_json_round_trip(self):
        payload = {"atom_strata": {"0": 12, "10": 4, "2": 9}}
        encoded = MODULE.json.dumps(payload)
        self.assertEqual(
            MODULE.canonical_digest(payload),
            MODULE.canonical_digest(MODULE.json.loads(encoded)),
        )

    def test_protocol_digest_is_available_to_freeze(self):
        protocol_path = SCRIPT.parent.parent / "PROTOCOL.json"
        protocol = MODULE.json.loads(protocol_path.read_text(encoding="utf-8"))
        self.assertEqual(protocol["schema_version"], "1.1")
        self.assertEqual(len(MODULE.canonical_digest(protocol)), 64)

    def test_atom_strata_cover_frozen_source_range(self):
        self.assertEqual(MODULE.atom_stratum(1), 0)
        self.assertEqual(MODULE.atom_stratum(30), 10)
        self.assertEqual(MODULE.atom_stratum(192), 15)
        with self.assertRaises(ValueError):
            MODULE.atom_stratum(0)
        with self.assertRaises(ValueError):
            MODULE.atom_stratum(193)

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
