import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("commit_panel", ROOT / "scripts" / "commit_panel.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def panel() -> dict:
    return {
        "schema_version": 1,
        "study_id": MODULE.EXPECTED_STUDY,
        "source_revision": MODULE.EXPECTED_REVISION,
        "nonce": "ab" * 32,
        "partitions": {"candidate": [101, 102], "held_out": [201, 202, 203]},
    }


class PanelCommitmentTest(unittest.TestCase):
    def test_public_record_hides_identities_and_nonce(self):
        record = MODULE.commitment(panel())
        rendered = str(record)
        self.assertNotIn("101", rendered)
        self.assertNotIn("201", rendered)
        self.assertNotIn("abab", rendered)
        self.assertEqual(record["partition_counts"], {"candidate": 2, "held_out": 3})

    def test_partition_overlap_is_rejected(self):
        payload = panel()
        payload["partitions"]["held_out"].append(101)
        with self.assertRaisesRegex(ValueError, "disjoint"):
            MODULE.validate_private_panel(payload)

    def test_commitment_changes_with_secret_payload(self):
        first = MODULE.commitment(panel())
        changed = panel()
        changed["partitions"]["candidate"][0] = 103
        second = MODULE.commitment(changed)
        self.assertNotEqual(first["commitment_sha256"], second["commitment_sha256"])


if __name__ == "__main__":
    unittest.main()
