"""Tests for the signal-density comparison instrument.

Run from this directory:  python3 -m unittest test_environment_ranking
"""

from __future__ import annotations

import unittest

import environment_ranking as ranking
import paired_design as ranking_pairing


class SymmetryTest(unittest.TestCase):
    def test_density_is_symmetric_about_one_half(self) -> None:
        for p in (0.035, 0.10, 0.25, 0.50, 0.75, 0.90):
            self.assertAlmostEqual(ranking.phi(p), ranking.phi(1 - p), places=12)

    def test_inverse_maps_back_to_the_chosen_side(self) -> None:
        for p in (0.05, 0.2, 0.4):
            value = ranking.phi(p)
            self.assertAlmostEqual(ranking.phi_roots(value, higher=False), p, places=12)
            self.assertAlmostEqual(ranking.phi_roots(value, higher=True), 1 - p, places=12)


class ComparisonTest(unittest.TestCase):
    def test_symmetric_pair_is_not_rejected(self) -> None:
        result = ranking.compare(40, 400, 360, 400)
        self.assertLess(result.likelihood_ratio, ranking.CHI_SQUARE_1DF_95)
        self.assertFalse(result.rejected_at_95)
        self.assertAlmostEqual(result.phi_a, result.phi_b, places=12)

    def test_distinct_densities_are_rejected(self) -> None:
        result = ranking.compare(12, 400, 46, 400)
        self.assertGreater(result.likelihood_ratio, ranking.CHI_SQUARE_1DF_95)
        self.assertTrue(result.rejected_at_95)
        self.assertGreater(result.phi_b, result.phi_a)

    def test_same_success_rate_at_different_trial_counts_is_not_rejected(self) -> None:
        result = ranking.compare(20, 400, 10, 200)
        self.assertAlmostEqual(result.p_a, result.p_b, places=12)
        self.assertLess(result.likelihood_ratio, ranking.CHI_SQUARE_1DF_95)


class DetectabilityTest(unittest.TestCase):
    def test_competing_density_needs_more_than_twice_the_signal(self) -> None:
        detectable = ranking.minimum_detectable(0.035, draws=150)
        self.assertGreater(detectable["higher"]["ratio"], 2.0)
        self.assertLess(detectable["higher"]["ratio"], 3.0)
        self.assertTrue(detectable["higher"]["power"] >= 0.8)


class PairingTest(unittest.TestCase):
    def test_mix_component_is_of_the_same_order_as_the_binomial_one(self) -> None:
        values = ranking_pairing.decomposition()
        self.assertGreater(values["mix_over_binomial"], 0.8)
        self.assertLess(values["mix_over_binomial"], 1.6)

    def test_pairing_shrinks_the_difference_and_the_detectable_ratio(self) -> None:
        values = ranking_pairing.decomposition()
        self.assertLess(values["paired_difference_sd"], values["unpaired_difference_sd"])
        self.assertGreater(values["paired_gain"], 1.4)
        self.assertLess(ranking_pairing.detectable_ratio(2.30), 1.7)

    def test_panel_proxy_stays_close_to_the_released_mass(self) -> None:
        self.assertTrue(ranking_pairing.decomposition()["proxy_close"])


class FragilityTest(unittest.TestCase):
    def test_bad_verifier_reverses_the_symmetric_pair(self) -> None:
        rows = ranking.verifier_symmetry_break(0.38)
        pair = {row["p"]: row for row in rows}
        self.assertGreater(pair[0.90]["ratio"], 4.0)
        self.assertLess(pair[0.10]["ratio"], 0.3)
        self.assertAlmostEqual(pair[0.50]["ratio"], 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
