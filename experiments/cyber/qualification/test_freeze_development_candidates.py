"""Tests for the probe/target partitioner.

Run from this directory:  python3 -m unittest test_freeze_development_candidates
Experiment-local scripts are not on the package `make test` discovery path, so
this suite is run manually and documented in the commit.
"""

from __future__ import annotations

import unittest

import freeze_development_candidates as fdc


def _ordering(task_ids: list[str]) -> list[dict[str, str | int]]:
    return fdc.ordered_rows("cybergym", task_ids)


class PartitionTest(unittest.TestCase):
    def setUp(self) -> None:
        # 400 synthetic tasks is enough to fill a 48 probe + 256 target split.
        self.tasks = [f"arvo:{i}" for i in range(400)]
        self.ordering = _ordering(self.tasks)

    def test_probe_is_first_by_rank_and_sized(self) -> None:
        part = fdc.partition_probe_and_target(self.ordering, probe_size=48)
        self.assertEqual(len(part["probe"]), 48)
        self.assertEqual(part["probe"], [str(r["task_id"]) for r in self.ordering[:48]])

    def test_probe_and_target_mutually_exclusive(self) -> None:
        part = fdc.partition_probe_and_target(self.ordering, probe_size=48, target_size=256)
        self.assertEqual(set(part["probe"]) & set(part["target"]), set())
        self.assertEqual(len(part["target"]), 256)
        self.assertTrue(part["audit"]["target_meets_minimum"])

    def test_deterministic(self) -> None:
        a = fdc.partition_probe_and_target(self.ordering, probe_size=48)
        b = fdc.partition_probe_and_target(_ordering(list(reversed(self.tasks))), probe_size=48)
        # Same salted ordering regardless of input order -> identical partitions.
        self.assertEqual(a["probe"], b["probe"])
        self.assertEqual(a["target"], b["target"])

    def test_identity_unresolved_without_map(self) -> None:
        part = fdc.partition_probe_and_target(self.ordering)
        self.assertFalse(part["audit"]["identity_resolved"])
        self.assertIn("UNRESOLVED", part["audit"]["disjointness"])

    def test_identity_key_disjointness_excludes_collisions(self) -> None:
        # Give every task a project; probe projects must not reappear in target.
        identity = {t: {"project": f"proj{i % 10}"} for i, t in enumerate(self.tasks)}
        part = fdc.partition_probe_and_target(
            self.ordering, probe_size=48, target_size=256, identity=identity
        )
        self.assertTrue(part["audit"]["identity_resolved"])
        probe_projects = {identity[t]["project"] for t in part["probe"]}
        target_projects = {identity[t]["project"] for t in part["target"]}
        self.assertEqual(probe_projects & target_projects, set())
        # With only 10 projects and all consumed by the 48-task probe, the target
        # must be empty and the minimum unmet -> honest failure, not a silent pass.
        self.assertEqual(len(part["target"]), 0)
        self.assertFalse(part["audit"]["target_meets_minimum"])
        self.assertGreater(part["audit"]["excluded_for_identity_collision"], 0)

    def test_identity_key_allows_disjoint_projects(self) -> None:
        # 200 distinct projects: probe uses <=48, leaving plenty disjoint.
        identity = {t: {"project": f"proj{i}"} for i, t in enumerate(self.tasks)}
        part = fdc.partition_probe_and_target(
            self.ordering, probe_size=48, target_size=256, identity=identity
        )
        probe_projects = {identity[t]["project"] for t in part["probe"]}
        target_projects = {identity[t]["project"] for t in part["target"]}
        self.assertEqual(probe_projects & target_projects, set())
        self.assertTrue(part["audit"]["target_meets_minimum"])


if __name__ == "__main__":
    unittest.main()
