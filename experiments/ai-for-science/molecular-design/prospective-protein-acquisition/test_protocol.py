from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProspectiveProteinProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads((ROOT / "FROZEN_CONTRACT.json").read_text())
        self.sources = json.loads((ROOT / "SOURCES.json").read_text())

    def test_panel_and_prediction_are_frozen(self) -> None:
        self.assertEqual(len(self.contract["candidate_datasets"]), 7)
        self.assertEqual(len(self.contract["strategies"]), 5)
        self.assertEqual(len(self.contract["seeds"]), 5)
        self.assertEqual(self.contract["release_gate"]["expected_units"], 175)
        self.assertEqual(self.contract["prediction"]["selected_strategy"], "greedy")

    def test_sources_match_panel_and_pass_outcome_blind_support(self) -> None:
        records = self.sources["dataset"]["files"]
        self.assertEqual(
            {record["dataset"] for record in records},
            set(self.contract["candidate_datasets"]),
        )
        minimum = self.contract["outcome_blind_support_gate"]["minimum_source_rows"]
        self.assertTrue(all(record["rows"] >= minimum for record in records))

    def test_candidate_cap_is_deterministic_and_outcome_independent(self) -> None:
        common = load_module("common")
        sequences = [f"SEQ{index}" for index in range(100)]
        left = common.deterministic_cap("test", sequences, list(range(100)), 20)
        right = common.deterministic_cap("test", sequences, list(reversed(range(100))), 20)
        self.assertEqual(left[0], right[0])
        self.assertEqual(left[2], right[2])

    def test_initial_batch_is_shared_across_strategies(self) -> None:
        runner = load_module("run_unit")
        sequences = [f"AAAA{index % 7}BBBB{index % 11}" for index in range(800)]
        targets = np.linspace(-1, 1, 800).tolist()
        first = runner.run_unit(sequences, targets, "amylase", "greedy", 7)
        second = runner.run_unit(sequences, targets, "amylase", "ucb", 7)
        self.assertEqual(
            first["selection_sha256_by_batch"][0],
            second["selection_sha256_by_batch"][0],
        )

    def test_freeze_binds_executable_protocol(self) -> None:
        freeze = json.loads((ROOT / "FREEZE.json").read_text())
        for relative, expected in freeze["files"].items():
            observed = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(observed, expected, relative)


if __name__ == "__main__":
    unittest.main()
