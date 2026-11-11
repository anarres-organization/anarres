"""Qualification tests for the Round 2 finance candidate resources."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "candidates"


def executable_namespace(candidate_id: str) -> dict[str, object]:
    text = (CANDIDATES / candidate_id / "SKILL.md").read_text()
    blocks = re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError(f"{candidate_id} must contain one Python block")
    namespace: dict[str, object] = {}
    exec(compile(blocks[0], f"{candidate_id}/SKILL.md", "exec"), namespace)
    return namespace


class FinanceCandidateQualificationTest(unittest.TestCase):
    def test_candidates_declare_scope_and_removal(self) -> None:
        for candidate_id in ("procedure", "executable", "combined"):
            text = (CANDIDATES / candidate_id / "SKILL.md").read_text().lower()
            self.assertRegex(text, r"task\s+instruction remains authoritative")
            self.assertIn("remove", text)
            self.assertIn("development", text)

    def test_candidate_sizes_respect_frozen_limits(self) -> None:
        limits = {"procedure": 12000, "executable": 24000, "combined": 36000}
        for candidate_id, limit in limits.items():
            size = (CANDIDATES / candidate_id / "SKILL.md").stat().st_size
            self.assertLessEqual(size, limit)

    def test_dcc_identity_has_zero_correlation_contribution(self) -> None:
        for candidate_id in ("executable", "combined"):
            helper = executable_namespace(candidate_id)["dcc_correlation_log_likelihood"]
            z = np.array([[0.2, -0.4], [1.0, 0.5]])
            correlations = np.repeat(np.eye(2)[None, :, :], len(z), axis=0)
            self.assertAlmostEqual(helper(z, correlations), 0.0)

    def test_stationary_bootstrap_is_deterministic_and_in_range(self) -> None:
        for candidate_id in ("executable", "combined"):
            helper = executable_namespace(candidate_id)["stationary_bootstrap_indices"]
            first = helper(17, 200, 1 / 21, 42)
            second = helper(17, 200, 1 / 21, 42)
            np.testing.assert_array_equal(first, second)
            self.assertTrue(np.all((first >= 0) & (first < 17)))

    def test_transition_total_uses_only_nondefault_origins(self) -> None:
        counts = np.zeros((2, 3, 3), dtype=int)
        counts[0, 0] = [3, 1, 1]
        counts[0, 1] = [0, 4, 2]
        counts[0, 2, 2] = 1
        counts[1, 0] = [2, 1, 0]
        counts[1, 1] = [1, 2, 1]
        counts[1, 2, 2] = 1
        for candidate_id in ("executable", "combined"):
            namespace = executable_namespace(candidate_id)
            sizes = namespace["nondefault_cohort_sizes"](counts, 2)
            total = namespace["reconcile_transition_total"](18, sizes)
            self.assertEqual(total, 18)
            with self.assertRaises(ValueError):
                namespace["reconcile_transition_total"](20, sizes)

    def test_tail_risk_uses_one_positive_loss_convention(self) -> None:
        losses = np.arange(1.0, 101.0)
        for candidate_id in ("executable", "combined"):
            helper = executable_namespace(candidate_id)["empirical_var_cvar"]
            var, cvar = helper(losses, 0.95)
            self.assertGreaterEqual(cvar, var)
            self.assertGreater(var, 0)


if __name__ == "__main__":
    unittest.main()
