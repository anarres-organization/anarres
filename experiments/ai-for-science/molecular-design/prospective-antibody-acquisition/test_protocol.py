from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProspectiveAntibodyProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads((ROOT / "FROZEN_CONTRACT.json").read_text())
        self.sources = json.loads((ROOT / "SOURCES.json").read_text())

    def test_panel_is_complete_and_prediction_is_frozen(self) -> None:
        self.assertEqual(len(self.contract["candidate_assays"]), 6)
        self.assertEqual(len(self.contract["strategies"]), 5)
        self.assertEqual(len(self.contract["seeds"]), 5)
        self.assertEqual(self.contract["release_gate"]["expected_units"], 150)
        self.assertEqual(self.contract["prediction"]["selected_strategy"], "ucb")
        self.assertEqual(self.contract["status"], "PROTOCOL_FROZEN__OUTCOMES_UNOPENED")

    def test_sources_match_candidate_assays_and_support_gate(self) -> None:
        records = self.sources["dataset"]["files"]
        self.assertEqual(
            {record["assay"] for record in records},
            set(self.contract["candidate_assays"]),
        )
        self.assertTrue(
            all(
                record["rows"] >= self.contract["outcome_blind_support_gate"]["minimum_rows"]
                for record in records
            )
        )
        self.assertTrue(all(len(record["sha256"]) == 64 for record in records))

    def test_initial_batch_is_shared_across_strategies(self) -> None:
        runner = load_module("run_unit")
        sequences = [f"AAAA{i % 7}|BBBB{i % 11}" for i in range(500)]
        outcomes = np.linspace(-1, 1, 500).tolist()
        first = runner.run_unit(sequences, outcomes, "1mlc", "random", 7)
        second = runner.run_unit(sequences, outcomes, "1mlc", "ucb", 7)
        self.assertEqual(
            first["selection_sha256_by_batch"][0],
            second["selection_sha256_by_batch"][0],
        )
        self.assertEqual(len(first["outcome"]["recall_curve"]), 10)

    def test_selection_rules_are_deterministic(self) -> None:
        runner = load_module("run_unit")
        candidates = np.arange(6)
        mean = np.asarray([0.1, 0.3, 0.2, 0.4, 0.6, 0.5])
        std = np.asarray([0.9, 0.1, 0.2, 0.3, 0.0, 0.4])
        rng = np.random.default_rng(1)
        self.assertEqual(
            runner.select_batch("greedy", mean, std, candidates, 2, rng).tolist(),
            [4, 5],
        )
        self.assertEqual(
            runner.select_batch("uncertainty", mean, std, candidates, 2, rng).tolist(),
            [0, 5],
        )

    def test_freeze_binds_executable_protocol(self) -> None:
        common = load_module("common")
        freeze = json.loads((ROOT / "FREEZE.json").read_text())
        for relative, expected in freeze["files"].items():
            self.assertEqual(common.sha256_path(ROOT / relative), expected, relative)


if __name__ == "__main__":
    unittest.main()
