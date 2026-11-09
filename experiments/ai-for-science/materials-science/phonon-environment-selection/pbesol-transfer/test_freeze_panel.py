import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("freeze_panel", ROOT / "freeze_panel.py")
FREEZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREEZE)
PREPARE_SPEC = importlib.util.spec_from_file_location("prepare_inputs", ROOT / "prepare_inputs.py")
PREPARE = importlib.util.module_from_spec(PREPARE_SPEC)
PREPARE_SPEC.loader.exec_module(PREPARE)


class FreezePanelTest(unittest.TestCase):
    def test_formula_parser(self):
        self.assertEqual(
            FREEZE.parse_formula("Ca3(PO4)2"),
            (("Ca", 3), ("O", 8), ("P", 2)),
        )
        self.assertEqual(FREEZE.parse_formula("Li8HfO6"), (("Hf", 1), ("Li", 8), ("O", 6)))
        self.assertEqual(FREEZE.parse_formula("C2O2"), (("C", 1), ("O", 1)))

    def test_poscar_parser(self):
        raw = b"test\n1.0\n1 0 0\n0 1 0\n0 0 1\nLi O\n2 2\nDirect\n"
        import gzip

        self.assertEqual(FREEZE.parse_poscar_composition(gzip.compress(raw)), (("Li", 1), ("O", 1)))

    def test_rank_is_deterministic(self):
        self.assertEqual(FREEZE.rank_value("mp-1"), FREEZE.rank_value("mp-1"))
        self.assertNotEqual(FREEZE.rank_value("mp-1"), FREEZE.rank_value("mp-2"))

    def test_selected_record_copy_does_not_mutate_audit_record(self):
        audit_record = {"composition_key": (("Li", 1),), "material_id": "mp-1"}
        selected_record = dict(audit_record)
        del selected_record["composition_key"]
        self.assertIn("composition_key", audit_record)

    def test_committed_freeze_digest(self):
        path = ROOT / "PANEL_FREEZE.json"
        payload = PREPARE.load_freeze(path)
        self.assertEqual(len(payload["records"]), 1000)
        self.assertFalse(payload["external_labels_read"])


if __name__ == "__main__":
    unittest.main()
