#!/usr/bin/env python3
"""Integrity checks for the source-recovered finance decision panels."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "recovered_panels.json"
SOURCES = ROOT / "SOURCES.json"
BUILDER = ROOT / "scripts" / "build_recovered_panels.py"


class RecoveredPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(BUILDER)], check=True, capture_output=True)
        cls.document = json.loads(DATA.read_text())
        cls.sources = json.loads(SOURCES.read_text())

    def test_support(self) -> None:
        panels = self.document["panels"]
        self.assertEqual(len(panels), 95)
        self.assertEqual(sum(len(panel["arms"]) for panel in panels), 391)
        self.assertEqual(sum(panel["budget_matched"] for panel in panels), 20)
        self.assertEqual(len({panel["source_id"] for panel in panels}), 10)

    def test_identity_and_values(self) -> None:
        panel_ids = [panel["panel_id"] for panel in self.document["panels"]]
        self.assertEqual(len(panel_ids), len(set(panel_ids)))
        for panel in self.document["panels"]:
            arm_ids = [arm["id"] for arm in panel["arms"]]
            self.assertEqual(len(arm_ids), len(set(arm_ids)))
            self.assertGreaterEqual(len(arm_ids), 2)
            for arm in panel["arms"]:
                self.assertTrue(math.isfinite(arm["score"]))
                self.assertIsInstance(arm["treatment"], dict)

    def test_every_source_is_registered(self) -> None:
        registered = {source["id"] for source in self.sources["sources"]}
        used = {panel["source_id"] for panel in self.document["panels"]}
        self.assertTrue(used <= registered)

    def test_claim_bearing_spot_checks(self) -> None:
        panels = {panel["panel_id"]: panel for panel in self.document["panels"]}
        fin_prm = {arm["id"]: arm["score"] for arm in panels["fin_prm_offline_selection"]["arms"]}
        self.assertEqual(fin_prm["random"], 43.8)
        self.assertEqual(fin_prm["fin_prm"], 58.2)
        fin_sd = {arm["id"]: arm["score"] for arm in panels["fin_sd_ablation"]["arms"]}
        self.assertEqual(fin_sd["self_rkl"], 72.19)
        self.assertEqual(fin_sd["long_rollout"], 71.09)
        mixture = {
            arm["id"]: arm["score"] for arm in panels["harsha_real_fraction_phi3_mini"]["arms"]
        }
        self.assertEqual(mixture["real_10"], 69.98)
        self.assertEqual(mixture["real_100"], 76.0)
        factorial = {
            arm["id"]: arm["score"] for arm in panels["shin_kim_qwen3p5_4b_kmmlu_finance"]["arms"]
        }
        self.assertEqual(factorial["base"], 50.61)
        self.assertEqual(factorial["exp2"], 52.16)
        finlcr = {arm["id"]: arm["score"] for arm in panels["finlcr_thresholds_docfinqa"]["arms"]}
        self.assertEqual(finlcr["0p2_0p8"], 47.29)
        self.assertEqual(finlcr["0p3_0p7"], 43.93)
        dianjin = {arm["id"]: arm["score"] for arm in panels["dianjin_qwen2p5_7b_finqa"]["arms"]}
        self.assertEqual(dianjin["all_sft"], 80.28)
        self.assertEqual(dianjin["all_sft_grpo"], 77.72)
        s2k = {arm["id"]: arm["score"] for arm in panels["s2k_qwen2p5_7b_stages"]["arms"]}
        self.assertEqual(s2k["raw"], 33.5)
        self.assertEqual(s2k["selective_sft_grpo"], 38.6)
        advice = {
            arm["id"]: arm["score"] for arm in panels["financial_advice_qwen3p5_27b_cate"]["arms"]
        }
        self.assertEqual(advice["base"], 0.0170)
        self.assertEqual(advice["finance_reward_grpo"], 0.0228)

    def test_alignment_is_relative_to_the_evaluation_target(self) -> None:
        panels = {panel["panel_id"]: panel for panel in self.document["panels"]}
        finqa = panels["phogat_t4_mistral_7b_finqa"]
        conv = panels["phogat_t4_mistral_7b_convfinqa"]
        self.assertEqual(finqa["arms"][0]["treatment"]["target_fraction"], 1.0)
        self.assertEqual(conv["arms"][0]["treatment"]["target_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()
