from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RetrospectiveBridgeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.invirtuo = json.loads((DATA / "invirtuo_replay_bridge_v1.json").read_text())
        cls.saturn = json.loads((DATA / "saturn_bridge_v1.json").read_text())
        cls.antoniuk = json.loads((DATA / "antoniuk_active_learning_bridge_v1.json").read_text())
        cls.tsmiles = json.loads((DATA / "tsmiles_jnk3_bridge_v1.json").read_text())
        cls.summary = json.loads((DATA / "retrospective_bridge_summary_v1.json").read_text())

    def test_pmo_summary_preserves_support_and_cost_boundary(self) -> None:
        pmo = self.summary["pmo"]
        self.assertEqual(pmo["support"]["methods"], 25)
        self.assertEqual(pmo["support"]["tasks"], 23)
        self.assertEqual(pmo["support"]["source_files"], 2875)
        self.assertEqual(pmo["support"]["normalized_records"], 14375)
        diagnostics = pmo["retrospective_pilot_diagnostics"]
        self.assertEqual([row["exact_final_winner_tasks"] for row in diagnostics], [8, 11, 14, 19])
        self.assertTrue(all("does not charge" in row["cost_note"] for row in diagnostics))

    def test_pmo_identity_parser_and_stable_batch_order(self) -> None:
        module = load_module("normalize_pmo")
        identity = module.parse_identity(Path("results_selfies_vae_bo_amlodipine_mpo_5.yaml"))
        self.assertEqual(identity, ("selfies_vae_bo", "amlodipine_mpo", "5"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.yaml"
            path.write_text("first: [0.2, 1]\nsecond: [0.9, 1]\nthird: [0.4, 2]\n")
            trace = module.load_trace(path)
        self.assertEqual([row[3] for row in trace], ["first", "second", "third"])

    def test_invirtuo_matched_panel(self) -> None:
        support = self.invirtuo["support"]
        self.assertEqual(support["tasks"], 23)
        self.assertEqual(support["matched_seed0_pairs"], 23)
        self.assertEqual(support["records"], 92)
        summary = self.invirtuo["matched_seed0_summary"]
        self.assertEqual(
            summary["replay_wins"] + summary["no_replay_wins"] + summary["ties"],
            23,
        )

    def test_saturn_panels_remain_distinct(self) -> None:
        support = self.saturn["support"]
        self.assertEqual(support["architecture_conditions"], 18)
        self.assertEqual(support["hit_ratio_records"], 200)
        self.assertEqual(
            {row["evidence_tier"] for row in self.saturn["architecture_records"]},
            {"direct_component_intervention_published_aggregate"},
        )

    def test_antoniuk_matches_budget_and_released_support(self) -> None:
        self.assertEqual(self.antoniuk["support"]["matched_dft_oracle_budget"], 500)
        self.assertEqual(self.antoniuk["support"]["released_molecule_records"], 61659)
        approaches = {row["approach"]: row for row in self.antoniuk["table_2_records"]}
        self.assertEqual(approaches["JANUS"]["dft_stable_count"], 31)
        self.assertEqual(
            approaches["JANUS w/Active Learning (this work)"]["dft_stable_count"],
            108,
        )

    def test_tsmiles_preserves_representation_boundary(self) -> None:
        self.assertEqual(self.tsmiles["support"]["published_conditions"], 21)
        best = max(self.tsmiles["records"], key=lambda row: row["active_novel_fraction"])
        self.assertEqual((best["condition"], best["training_rounds"]), ("TSSA_S_Rec50", 10))
        self.assertIn("not a fixed-trainer", self.tsmiles["claim_boundary"])

    def test_summary_preserves_five_scientific_objects(self) -> None:
        self.assertEqual(self.summary["source_objects"], 5)
        self.assertEqual(
            self.summary["invirtuogen_replay"]["matched_seed0_summary"]["replay_wins"],
            12,
        )
        self.assertEqual(
            self.summary["saturn"]["winner_counts"],
            {"GEAM": 1, "Saturn (Framework)": 4},
        )
        self.assertIn("RxnFlow", self.summary["claim_boundary"])

    def test_release_manifest(self) -> None:
        repository = ROOT.parents[3]
        for line in (ROOT / "MANIFEST.sha256").read_text().splitlines():
            expected, relative_path = line.split("  ", maxsplit=1)
            digest = hashlib.sha256((repository / relative_path).read_bytes()).hexdigest()
            self.assertEqual(digest, expected, relative_path)


if __name__ == "__main__":
    unittest.main()
