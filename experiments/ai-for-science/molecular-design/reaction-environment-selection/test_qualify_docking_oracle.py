import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "qualify_docking_oracle.py"
SPEC = importlib.util.spec_from_file_location("qualify_docking_oracle", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class Vector(list):
    def __add__(self, other):
        if isinstance(other, (int, float)):
            return Vector(item + other for item in self)
        return Vector(self[index] + other[index] for index in range(len(self)))

    def __sub__(self, other):
        return Vector(self[index] - other[index] for index in range(len(self)))

    def __truediv__(self, value):
        return Vector(item / value for item in self)

    def tolist(self):
        return list(self)


class Positions:
    def min(self, axis):
        assert axis == 0
        return Vector([0.0, 1.0, 2.0])

    def max(self, axis):
        assert axis == 0
        return Vector([4.0, 7.0, 10.0])


class QualifyDockingOracleTests(unittest.TestCase):
    def test_reference_box_matches_reference_ligand_extent(self):
        center, size = MODULE.reference_box(Positions(), 5.0)
        self.assertEqual(center, [2.0, 4.0, 6.0])
        self.assertEqual(size, [9.0, 11.0, 13.0])

    def test_summarize_runs_passes_stable_reference_control(self):
        runs = [
            {"seed": 1, "repeat": 0, "status": "ok", "affinity": -7.2},
            {"seed": 1, "repeat": 1, "status": "ok", "affinity": -7.2},
            {"seed": 2, "repeat": 0, "status": "ok", "affinity": -6.9},
            {"seed": 2, "repeat": 1, "status": "ok", "affinity": -6.9},
        ]
        summary = MODULE.summarize_runs(runs, MODULE.GateContract())
        self.assertEqual(summary["qualification"], "pass")
        self.assertAlmostEqual(summary["median_reference_affinity"], -7.05)

    def test_summarize_runs_fails_infrastructure_error(self):
        runs = [
            {"seed": 1, "repeat": 0, "status": "ok", "affinity": -7.0},
            {"seed": 1, "repeat": 1, "status": "infrastructure_failure"},
        ]
        summary = MODULE.summarize_runs(runs, MODULE.GateContract())
        self.assertEqual(summary["qualification"], "fail")
        self.assertFalse(summary["checks"]["all_calls_succeeded"])


if __name__ == "__main__":
    unittest.main()
