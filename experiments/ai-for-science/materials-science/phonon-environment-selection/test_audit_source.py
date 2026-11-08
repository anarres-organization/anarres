import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "audit_source.py"
SPEC = importlib.util.spec_from_file_location("audit_source", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SourceAuditTest(unittest.TestCase):
    def test_formula_elements_handles_parentheses_and_counts(self):
        self.assertEqual(MODULE.formula_elements("Yb19(Mg4H27)2"), {"Yb", "Mg", "H"})
        self.assertEqual(MODULE.formula_elements("Na2Pd3O4"), {"Na", "Pd", "O"})

    def test_missing_required_files_fail(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            MODULE.audit(Path(directory))

    def test_expected_roles_are_explicit(self):
        self.assertEqual(
            MODULE.EXPECTED_ROLES,
            {
                "gradient_train": 7809,
                "checkpoint_validation": 411,
                "unused_rounding": 1,
            },
        )

    def test_sources_file_is_valid_json(self):
        path = Path(__file__).parent / "SOURCES.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(source["local_use_boundary"]["external_labels_inspected_for_this_study"])


if __name__ == "__main__":
    unittest.main()
