"""Unit tests for the credential-safe QF-Bench runner."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_task


class NativeQFBenchRunnerTest(unittest.TestCase):
    def test_frozen_task_index_covers_all_partitions(self) -> None:
        indexed = run_task.frozen_tasks()
        self.assertEqual(len(indexed), 10)
        self.assertEqual(indexed["historical-var-data-prep"]["partition"], "development")
        self.assertEqual(indexed["standard-var-methods"]["partition"], "target")
        self.assertEqual(
            indexed["ewma-portfolio-risk-decomposition"]["partition"], "shared_protected"
        )

    def test_prepare_exposes_only_agent_visible_inputs(self) -> None:
        task_id = "historical-var-data-prep"
        instruction = b"Do the task.\n"
        task_toml = b"[agent]\ntimeout_sec = 10\n"
        with tempfile.TemporaryDirectory() as temporary:
            qfbench = Path(temporary) / "qfbench"
            task = qfbench / "tasks" / task_id
            (task / "environment" / "data").mkdir(parents=True)
            (task / "tests").mkdir()
            (task / "solution").mkdir()
            (task / "instruction.md").write_bytes(instruction)
            (task / "task.toml").write_bytes(task_toml)
            (task / "environment" / "data" / "input.csv").write_text("x\n1\n")
            (task / "tests" / "secret.py").write_text("secret")
            (task / "solution" / "solve.sh").write_text("secret")
            stage = Path(temporary) / "stage"
            row = {
                "task_id": task_id,
                "partition": "development",
                "round": 1,
                "task_toml_sha256": hashlib.sha256(task_toml).hexdigest(),
                "instruction_sha256": hashlib.sha256(instruction).hexdigest(),
            }
            with (
                mock.patch.object(run_task, "frozen_tasks", return_value={task_id: row}),
                mock.patch.object(
                    run_task,
                    "run_checked",
                    return_value=mock.Mock(
                        stdout=json.loads(run_task.SOURCE_PATH.read_text())["commit"]
                    ),
                ),
            ):
                manifest = run_task.prepare_stage(qfbench, task_id, stage, None)
            self.assertEqual(
                manifest["agent_visible_entries"],
                ["data", "instruction.md", "output"],
            )
            self.assertFalse((stage / "tests").exists())
            self.assertFalse((stage / "solution").exists())
            self.assertEqual(
                sorted(path.name for path in stage.iterdir()),
                ["data", "instruction.md", "output"],
            )
            self.assertTrue((run_task.record_root(stage) / "STAGE_MANIFEST.json").is_file())


if __name__ == "__main__":
    unittest.main()
