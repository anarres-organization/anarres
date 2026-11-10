"""Integrity test for the frozen Square measurement contract."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
SPECIFICATION = importlib.util.spec_from_file_location(
    "square_freeze_verifier", ROOT / "scripts/verify_freeze.py"
)
assert SPECIFICATION is not None and SPECIFICATION.loader is not None
MODULE = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(MODULE)


class SquareFreezeTests(unittest.TestCase):
    def test_frozen_artifacts_are_consistent(self) -> None:
        report = MODULE.verify()
        self.assertEqual(report["states"], 128)
        self.assertEqual(report["strata"], 8)
        self.assertFalse(report["candidate_outcomes_opened"])


if __name__ == "__main__":
    unittest.main()
