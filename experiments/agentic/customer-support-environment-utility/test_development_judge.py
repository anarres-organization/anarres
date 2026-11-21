import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).parent / "scripts" / "score_development_traces.py"
SPEC = importlib.util.spec_from_file_location("score_development_traces", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class FakeStateDiff:
    def __init__(self, *, created, modified, deleted):
        self.created = created
        self.modified = modified
        self.deleted = deleted


class FakeTaskDefinition:
    @classmethod
    def load(cls, path):
        del path
        return SimpleNamespace(
            task_requirements=[{"id": "communicated"}], task_type="exchange_item"
        )


class FakeJudge:
    def __init__(self, **kwargs):
        del kwargs

    def evaluate(self, task, conversation, tool_calls, state_diff):
        del task, conversation, tool_calls, state_diff
        return SimpleNamespace(
            score=1,
            details=[{"id": "communicated", "passed": True}],
            reasoning="passed",
        )


class FakeClient:
    def __init__(self):
        self.context = None

    def set_context(self, *, task_id, run_index):
        self.context = (task_id, run_index)


class FakeEfficiency:
    def to_dict(self):
        return {"turns": 1, "tool_calls": 0, "tool_errors": 0, "redundant_calls": 0}


class DevelopmentJudgeTest(unittest.TestCase):
    def test_request_disables_thinking(self):
        client = object.__new__(MODULE.LocalJudgeClient)
        client.model = "Qwen/Qwen3-32B"
        client.seed = 1729
        parameters = client.request_parameters([{"role": "user", "content": "test"}], 64)
        self.assertEqual(
            parameters["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": False}},
        )
        self.assertEqual(parameters["temperature"], 0)
        self.assertEqual(parameters["seed"], 1729)

    def test_sidecar_is_separate_and_content_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trajectory = root / "run1" / "task-a.json"
            trajectory.parent.mkdir()
            trajectory.write_text(
                json.dumps(
                    {
                        "task_id": "task-a",
                        "conversation": [{"role": "assistant", "content": "done"}],
                        "state_diff": {"created": {}, "modified": {}, "deleted": {}},
                    }
                ),
                encoding="utf-8",
            )
            original = trajectory.read_bytes()
            task = root / "task-a.json"
            task.write_text("{}", encoding="utf-8")
            output = root / "scores" / "run1" / "task-a.json"
            client = FakeClient()
            state_result = SimpleNamespace(score=1, reasoning="passed", details=None)
            modules = {
                "StateDiff": FakeStateDiff,
                "TaskDefinition": FakeTaskDefinition,
                "TaskRequirementsJudge": FakeJudge,
                "get_domain_config": lambda _: SimpleNamespace(
                    prompts_dir=root, judge_system_prompt="judge"
                ),
                "evaluate_state_requirements": lambda task, diff: state_result,
                "combine_task_completion": lambda state, task: int(
                    state.score == 1 and task.score == 1
                ),
                "compute_efficiency": lambda conversation, calls: FakeEfficiency(),
            }
            contract = {"contract_sha256": "a" * 64}
            payload = MODULE.score_one(
                checkout=root,
                trajectory_path=trajectory,
                task_path=task,
                output_path=output,
                run_index=1,
                client=client,
                modules=modules,
                contract=contract,
                source_revision="b" * 40,
            )
            self.assertEqual(trajectory.read_bytes(), original)
            self.assertFalse(payload["official_state_bench_compatible"])
            self.assertEqual(payload["scores"]["task_completion_pass"], 1)
            self.assertEqual(client.context, ("task-a", 1))
            MODULE.score_one(
                checkout=root,
                trajectory_path=trajectory,
                task_path=task,
                output_path=output,
                run_index=1,
                client=client,
                modules=modules,
                contract=contract,
                source_revision="b" * 40,
            )
            changed_contract = {"contract_sha256": "c" * 64}
            with self.assertRaisesRegex(ValueError, "different sidecar"):
                MODULE.score_one(
                    checkout=root,
                    trajectory_path=trajectory,
                    task_path=task,
                    output_path=output,
                    run_index=1,
                    client=client,
                    modules=modules,
                    contract=changed_contract,
                    source_revision="b" * 40,
                )


if __name__ == "__main__":
    unittest.main()
