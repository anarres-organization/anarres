import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("run_checkpoint_evaluation_matrix.py")
SPEC = importlib.util.spec_from_file_location("run_checkpoint_evaluation_matrix", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_worker_shards_cover_checkpoint_matrix_once(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "environments": {"development": [{"candidate_id": "a"}, {"candidate_id": "b"}]},
                "randomization": {"training_seeds": [0, 1]},
                "environment_budget": {"checkpoints_after_passes": [1, 2]},
            }
        ),
        encoding="utf-8",
    )
    shards = [MODULE.tasks(contract, index, 3) for index in range(3)]
    observed = {
        (task["candidate_id"], task["seed"], task["epoch"]) for shard in shards for task in shard
    }
    assert len(observed) == 8


def test_prospective_role_uses_only_prospective_environments(tmp_path):
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "environments": {
                    "development": [{"candidate_id": "development"}],
                    "prospective": [{"candidate_id": "heldout"}],
                },
                "randomization": {"training_seeds": [0, 1]},
                "environment_budget": {"checkpoints_after_passes": [1, 2]},
            }
        ),
        encoding="utf-8",
    )
    tasks = MODULE.tasks(contract, 0, 1, "prospective")
    assert {task["candidate_id"] for task in tasks} == {"heldout"}
    assert len(tasks) == 4
