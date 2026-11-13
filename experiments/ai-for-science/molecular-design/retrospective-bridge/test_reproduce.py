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
        cls.pmo_decisions = json.loads((DATA / "pmo_decision_ladder_v1.json").read_text())
        cls.prediction_contract = json.loads((DATA / "prediction_contract_v1.json").read_text())
        cls.decision_uncertainty = json.loads((DATA / "decision_uncertainty_v1.json").read_text())
        cls.vantilborg = json.loads(
            (DATA / "vantilborg_active_learning_bridge_v1.json").read_text()
        )
        cls.reisman = json.loads((DATA / "reisman_regioselectivity_bridge_v1.json").read_text())
        cls.explainable_al = json.loads(
            (DATA / "explainable_active_learning_bridge_v1.json").read_text()
        )
        cls.rubisco_al = json.loads((DATA / "rubisco_active_learning_bridge_v1.json").read_text())

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

    def test_pmo_decision_ladder_charges_measurement_and_changes_decisions(self) -> None:
        self.assertEqual(self.pmo_decisions["support"]["tasks"], 23)
        self.assertEqual(self.pmo_decisions["support"]["candidate_methods"], 25)
        primary = self.pmo_decisions["budget_results"][0]
        self.assertEqual(primary["pilot_budget_per_method_run"], 1000)
        self.assertEqual(
            primary["prior_plus_pilot_auc_decisions_different_from_fixed_method"],
            18,
        )
        learned = primary["metrics"]["prior_plus_pilot_auc"]
        fixed = primary["metrics"]["training_fold_fixed_method"]
        self.assertLess(learned["normalized_regret"], fixed["normalized_regret"])
        self.assertGreater(learned["pairwise_ordering"], fixed["pairwise_ordering"])
        self.assertAlmostEqual(
            primary["mean_primary_rule_cost"]["fraction_of_exhaustive"],
            0.142261069926,
        )
        pairing = primary["pilot_pairing_control"]
        self.assertEqual(pairing["repeats"], 1000)
        self.assertAlmostEqual(
            pairing["fraction_null_as_good_or_better_regret"],
            1 / 1001,
        )

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

    def test_vantilborg_audit_preserves_support_and_held_out_decisions(self) -> None:
        self.assertEqual(
            self.vantilborg["source_sha256"],
            "646a4b499ebcb0ad2681ebee708bc61f69cd47fee1674b3d6ebaedc9256dc8f0",
        )
        support = self.vantilborg["support"]
        self.assertEqual(support["primary_datasets"], ["ALDH1", "PKM2", "VDR"])
        self.assertEqual(support["contexts"], 9)
        self.assertEqual(support["condition_records"], 54)
        self.assertEqual(support["run_records"], 540)
        method_architecture = self.vantilborg["leave_one_dataset_out"]["method_by_architecture"]
        fixed = self.vantilborg["training_fold_fixed_method"]
        self.assertAlmostEqual(method_architecture["pairwise_ordering"], 0.837037037037037)
        self.assertAlmostEqual(method_architecture["mean_normalized_regret"], 0.13765510137191553)
        self.assertGreater(method_architecture["pairwise_ordering"], fixed["pairwise_ordering"])

    def test_reisman_audit_preserves_support_and_decision_boundary(self) -> None:
        support = self.reisman["support"]
        self.assertEqual(support["targets"], 50)
        self.assertEqual(support["conditions"], 500)
        self.assertEqual(support["released_runs"], 14998)
        self.assertEqual(support["conditions_with_29_runs"], 2)
        audit = self.reisman["stable_top1_decision_audit"]
        structural = audit["structural_nearest_target"]
        fixed = audit["training_fold_fixed_method"]
        self.assertAlmostEqual(structural["best_method_credit"], 0.62)
        self.assertLess(structural["mean_normalized_regret"], fixed["mean_normalized_regret"])
        self.assertLess(structural["pairwise_ordering"], fixed["pairwise_ordering"])
        nested = audit["nested_similarity_weighted"]
        self.assertGreater(nested["pairwise_ordering"], fixed["pairwise_ordering"])
        self.assertLess(nested["mean_normalized_regret"], fixed["mean_normalized_regret"])

    def test_reisman_parser_preserves_overlapping_method_names(self) -> None:
        module = load_module("normalize_reisman_regioselectivity")
        name = "clean_run/res_rf_CCO_acqf_2-1_30_1_coldstart_custom.pkl"
        self.assertEqual(module.parse_identity(name), ("CCO", "acqf_2-1", 30))
        self.assertEqual(module.stable_index([0.2] * 3 + [0.95] * 10), 12)

    def test_explainable_al_preserves_complete_panels_and_nested_holdout(self) -> None:
        self.assertEqual(
            self.explainable_al["source_sha256"],
            "2e6b7a7b1df02524423f6c86e0d8f0c51427809ef175daa9185ffe3464e3cddf",
        )
        support = self.explainable_al["support"]
        self.assertEqual(support["datasets"], ["D2R", "MPRO", "TYK2", "USP7"])
        self.assertEqual(support["trajectory_rows"], 13_860)
        self.assertEqual(support["complete_runs"], 1_260)
        self.assertEqual(support["decision_panels"], 60)
        primary = self.explainable_al["leave_one_dataset_out"]["primary_global_protocol"]
        endpoint = self.explainable_al["endpoint_sensitivity"]["leave_one_dataset_out"]
        self.assertAlmostEqual(primary["pairwise_ordering"], 0.6662698412698412)
        self.assertAlmostEqual(primary["mean_normalized_regret"], 0.26793592407619216)
        self.assertAlmostEqual(
            endpoint["nested_view_selection"]["pairwise_ordering"],
            0.6353174603174603,
        )
        self.assertAlmostEqual(
            endpoint["nested_view_selection"]["mean_normalized_regret"],
            0.24647162871303208,
        )
        self.assertLess(
            primary["mean_normalized_regret"],
            self.explainable_al["baselines"]["uninformed_tie"]["mean_normalized_regret"],
        )
        self.assertEqual(len(self.explainable_al["budget_specific_sensitivity"]), 10)
        self.assertEqual(
            set(endpoint["nested_view_selection"]["chosen_view_by_held_out_dataset"]),
            set(support["datasets"]),
        )

    def test_rubisco_external_direction_preserves_common_budget_and_replicates(self) -> None:
        support = self.rubisco_al["support"]
        self.assertEqual(support["complete_runs"], 100)
        self.assertEqual(support["common_budget_end_by_dataset"], {"DMS": 1208, "HOFF": 1400})
        results = self.rubisco_al["directional_results"]
        self.assertEqual([row["replicates_with_positive_difference"] for row in results], [10, 9])
        self.assertTrue(all(row["paired_difference_95_interval"][0] > 0 for row in results))

    def test_summary_preserves_nine_scientific_objects(self) -> None:
        self.assertEqual(self.summary["source_objects"], 9)
        self.assertEqual(
            self.summary["invirtuogen_replay"]["matched_seed0_summary"]["replay_wins"],
            12,
        )
        self.assertEqual(
            self.summary["saturn"]["winner_counts"],
            {"GEAM": 1, "Saturn (Framework)": 4},
        )
        self.assertIn("RxnFlow", self.summary["claim_boundary"])
        self.assertEqual(self.summary["vantilborg_active_learning"]["support"]["contexts"], 9)
        self.assertEqual(self.summary["reisman_regioselectivity"]["support"]["targets"], 50)
        self.assertEqual(
            self.summary["explainable_active_learning"]["support"]["decision_panels"],
            60,
        )
        self.assertEqual(self.summary["rubisco_active_learning"]["support"]["complete_runs"], 100)

    def test_prediction_contract_separates_timing_cost_and_eligibility(self) -> None:
        contract = self.prediction_contract
        self.assertEqual(len(contract["prediction_audits"]), 4)
        self.assertEqual(len(contract["supporting_objects"]), 5)
        self.assertFalse(contract["prediction_audits"]["pmo_temporal"]["pretraining_profile_input"])
        self.assertEqual(contract["prospective_boundary"]["status"], "released")
        self.assertIn("abstains", contract["prospective_boundary"]["interpretation"])
        self.assertIn(
            "source-construction asset",
            contract["prospective_boundary"]["explore_template"],
        )

    def test_decision_uncertainty_resamples_complete_contexts(self) -> None:
        audit = self.decision_uncertainty
        self.assertEqual(audit["method"]["resamples"], 20_000)
        self.assertEqual(audit["vantilborg_cross_library"]["independent_contexts"], 3)
        self.assertEqual(audit["reisman_cross_target_nearest"]["independent_contexts"], 50)
        self.assertGreater(
            audit["reisman_cross_target_nearest"]["bootstrap_frequency_primary_lower_regret"],
            0.9,
        )
        self.assertLess(
            audit["reisman_cross_target_nearest"][
                "primary_minus_baseline_best_choice_credit_95_interval"
            ][0],
            audit["reisman_cross_target_nearest"][
                "primary_minus_baseline_best_choice_credit_95_interval"
            ][1],
        )

    def test_release_manifest(self) -> None:
        repository = ROOT.parents[3]
        for line in (ROOT / "MANIFEST.sha256").read_text().splitlines():
            expected, relative_path = line.split("  ", maxsplit=1)
            digest = hashlib.sha256((repository / relative_path).read_bytes()).hexdigest()
            self.assertEqual(digest, expected, relative_path)


if __name__ == "__main__":
    unittest.main()
