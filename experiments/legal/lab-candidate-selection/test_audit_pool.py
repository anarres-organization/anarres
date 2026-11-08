"""Scientific partition checks for the LAB source-pool auditor."""

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "audit_pool.py"
SPEC = importlib.util.spec_from_file_location("audit_pool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
sys.path.insert(0, str(SCRIPT.parent))
from build_candidate_bank import bank  # noqa: E402
from document_blobs import (  # noqa: E402
    screen_document_blobs,
    screen_exact_titles,
    verify_task_hashes,
)


class SourcePoolAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        ids = [
            "area/a/scenario-01",
            "area/a/scenario-02",
            "area/b/scenario-01",
            "area/b/scenario-02",
            "area/c",
            "area/d",
        ]
        self.rows = [
            {
                "task_id": task_id,
                "task_sha256": f"{index:064x}",
                "practice_area": "area",
                "work_type": "review",
                "shared_document_corpus": index == 5,
                "outcomes_read": False,
            }
            for index, task_id in enumerate(ids, 1)
        ]
        self.inventory = self.root / "inventory.jsonl"
        self.inventory.write_text(
            "\n".join(json.dumps(row) for row in self.rows) + "\n", encoding="utf-8"
        )
        self.probe = self.root / "probe.json"
        self.target = self.root / "target.json"
        self.write_panel(self.probe, [ids[0]])
        self.write_panel(self.target, [ids[2]])

    def write_panel(self, path: Path, ids: list[str], outcomes_read: bool = False) -> None:
        hashes = {row["task_id"]: row["task_sha256"] for row in self.rows}
        path.write_text(
            json.dumps(
                {
                    "task_ids": ids,
                    "task_hashes": {task_id: hashes[task_id] for task_id in ids},
                    "outcomes_read": outcomes_read,
                }
            ),
            encoding="utf-8",
        )

    def test_excludes_related_scenarios_and_shared_documents(self) -> None:
        result = MODULE.audit(self.inventory, self.probe, self.target)
        self.assertEqual(result["eligible_tasks"], 1)
        self.assertEqual(result["excluded"]["shared_scenario_family"], 2)
        self.assertEqual(result["excluded"]["shared_document_corpus"], 1)
        self.assertFalse(result["outcomes_read"])

    def test_refuses_opened_target(self) -> None:
        self.write_panel(self.target, [self.rows[2]["task_id"]], outcomes_read=True)
        with self.assertRaisesRegex(ValueError, "not outcome-blind"):
            MODULE.audit(self.inventory, self.probe, self.target)

    def test_refuses_hash_drift(self) -> None:
        payload = json.loads(self.target.read_text())
        payload["task_hashes"][self.rows[2]["task_id"]] = "f" * 64
        self.target.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash differs"):
            MODULE.audit(self.inventory, self.probe, self.target)

    def test_refuses_unexpected_panel_payload(self) -> None:
        payload = json.loads(self.target.read_text())
        payload["scores"] = [1]
        self.target.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected panel fields"):
            MODULE.audit(self.inventory, self.probe, self.target)

    def test_refuses_unexpected_inventory_payload(self) -> None:
        self.rows[0]["reward"] = 1
        self.inventory.write_text(
            "\n".join(json.dumps(row) for row in self.rows) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "unexpected inventory fields"):
            MODULE.audit(self.inventory, self.probe, self.target)

    def test_candidate_bank_uses_same_support_and_normalized_weights(self) -> None:
        rows = [
            {
                "task_id": f"task-{i}",
                "task_sha256": f"{i:064x}",
                "practice_area": "a" if i < 6 else "b",
                "criteria_count": i,
            }
            for i in range(1, 9)
        ]
        result = bank(rows)
        self.assertEqual(result["task_count"], 8)
        self.assertEqual(result["rubric_dense_cutoff"], 6)
        self.assertFalse(result["outcomes_read"])
        for candidate in result["candidates"].values():
            self.assertEqual(set(candidate["weights"]), set(result["task_hashes"]))
            self.assertAlmostEqual(sum(candidate["weights"].values()), 1)
        self.assertGreater(
            result["total_variation"]["source_proportional__practice_area_balanced"], 0
        )

    def test_candidate_bank_rejects_one_area(self) -> None:
        rows = [
            {
                "task_id": f"task-{i}",
                "task_sha256": f"{i:064x}",
                "practice_area": "a",
                "criteria_count": i,
            }
            for i in range(4)
        ]
        with self.assertRaisesRegex(ValueError, "two practice areas"):
            bank(rows)

    def test_exact_document_screen_excludes_candidate_reuse(self) -> None:
        repo = self.root / "source"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for task_id, document in (
            ("area/probe", "probe"),
            ("area/target", "shared"),
            ("area/candidate-shared", "shared"),
            ("area/candidate-unique", "unique"),
        ):
            task = repo / "tasks" / task_id
            (task / "documents").mkdir(parents=True)
            (task / "task.json").write_text("{}", encoding="utf-8")
            (task / "documents" / "matter.txt").write_text(document, encoding="utf-8")
        subprocess.run(["git", "add", "tasks"], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=repo,
            check=True,
        )
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
        task_hash = hashlib.sha256(b"{}").hexdigest()
        self.assertEqual(
            verify_task_hashes(
                repo,
                {
                    task_id: task_hash
                    for task_id in (
                        "area/probe",
                        "area/target",
                        "area/candidate-shared",
                        "area/candidate-unique",
                    )
                },
                revision=revision,
            ),
            4,
        )
        eligible = [
            {"task_id": "area/candidate-shared"},
            {"task_id": "area/candidate-unique"},
        ]
        remaining, summary = screen_document_blobs(
            repo, eligible, {"area/probe"}, {"area/target"}, revision=revision
        )
        self.assertEqual([row["task_id"] for row in remaining], ["area/candidate-unique"])
        self.assertEqual(summary["excluded_candidate_tasks"], 1)
        self.assertEqual(summary["exact_blob_collisions_with_target"], 1)
        self.assertNotIn("area/target", json.dumps(summary))
        (repo / "tasks" / "area" / "candidate-unique" / "task.json").write_text(
            '{"changed":true}', encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "differs from the inventory"):
            verify_task_hashes(
                repo,
                {"area/candidate-unique": task_hash},
                revision=revision,
            )

    def test_exact_title_screen_excludes_candidate_reuse(self) -> None:
        repo = self.root / "source"
        for task_id, title in (
            ("area/probe", "Probe task"),
            ("area/target", "Review merger agreement"),
            ("area/same-title", "  review  merger agreement  "),
            ("area/unique", "Draft a notice"),
        ):
            task = repo / "tasks" / task_id
            task.mkdir(parents=True)
            (task / "task.json").write_text(json.dumps({"title": title}), encoding="utf-8")
        remaining, summary = screen_exact_titles(
            repo,
            [{"task_id": "area/same-title"}, {"task_id": "area/unique"}],
            {"area/probe"},
            {"area/target"},
        )
        self.assertEqual([row["task_id"] for row in remaining], ["area/unique"])
        self.assertEqual(summary["exact_title_matches_with_target"], 1)
        self.assertNotIn("area/target", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
