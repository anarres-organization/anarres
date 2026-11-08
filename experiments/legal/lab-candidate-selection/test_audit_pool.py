"""Scientific partition checks for the LAB source-pool auditor."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "audit_pool.py"
SPEC = importlib.util.spec_from_file_location("audit_pool", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


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


if __name__ == "__main__":
    unittest.main()
