#!/usr/bin/env python3
"""Integrity and leakage-boundary checks for the checked-in Grug corpus."""

from __future__ import annotations

import gzip
import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as stream:
        return [json.loads(line) for line in stream]


class GrugSwarmCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((HERE / "GRUG_SWARM_CORPUS.json").read_text())
        cls.inputs = read_rows(HERE / "GRUG_SWARM_INPUTS.jsonl.gz")
        cls.labels = read_rows(HERE / "GRUG_SWARM_PROTECTED_LABELS.jsonl.gz")

    def test_artifacts_match_manifest(self) -> None:
        for key in ("inputs", "protected_labels"):
            artifact = self.manifest["artifacts"][key]
            self.assertEqual(digest(HERE / artifact["path"]), artifact["sha256"])

    def test_released_units_are_not_multiplied_by_targets(self) -> None:
        summary = self.manifest["summary"]
        self.assertEqual(len(self.inputs), 934)
        self.assertEqual(len(self.labels), 934)
        self.assertEqual(summary["candidate_lineages"], 915)
        self.assertEqual(summary["protected_targets_per_run"], 162)
        families = self.manifest["evaluation_contract"]["target_families"]
        self.assertEqual(len(families["capability_log_probability"]), 54)
        self.assertEqual(len(families["held_out_loss_or_bpb"]), 108)

    def test_inputs_and_protected_labels_are_separate(self) -> None:
        input_keys = {row["record_key"] for row in self.inputs}
        label_keys = {row["record_key"] for row in self.labels}
        self.assertEqual(input_keys, label_keys)
        self.assertFalse(any("outcomes" in row for row in self.inputs))
        self.assertFalse(any("prediction_time" in row for row in self.labels))

    def test_lineages_keep_replicates_together(self) -> None:
        counts: dict[str, int] = {}
        for row in self.inputs:
            counts[row["lineage_key"]] = counts.get(row["lineage_key"], 0) + 1
        self.assertEqual(len(counts), 915)
        self.assertEqual(sum(count > 1 for count in counts.values()), 9)
        self.assertEqual(self.manifest["evaluation_contract"]["split_unit"], "candidate lineage")

    def test_full_two_phase_environment_is_retained(self) -> None:
        for row in self.inputs:
            prediction = row["prediction_time"]
            self.assertEqual(len(prediction["phase0_cell_weights"]), 200)
            self.assertEqual(len(prediction["phase1_cell_weights"]), 200)
            self.assertAlmostEqual(sum(prediction["phase0_cell_weights"]), 1.0)
            self.assertAlmostEqual(sum(prediction["phase1_cell_weights"]), 1.0)


if __name__ == "__main__":
    unittest.main()
