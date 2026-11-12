import importlib.util
import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).parent / "scripts" / "materialize_replay_bank.py"
SPEC = importlib.util.spec_from_file_location("materialize_replay_bank", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


@dataclass(frozen=True)
class FakeActionType:
    is_unirxn: bool


@dataclass(frozen=True)
class FakeAction:
    name: str
    action_type: FakeActionType


class FakeReplay:
    def __init__(self, capacity=8):
        self.capacity = capacity
        self.state = None

    def __len__(self):
        return 0 if self.state is None else len(self.state["items"])

    def load_state_dict(self, state):
        self.state = state


class MaterializeReplayBankTests(unittest.TestCase):
    def test_backward_probability_matches_synthon_weighted_route_mass(self):
        observed = FakeAction("observed", FakeActionType(is_unirxn=False))
        other = FakeAction("other", FakeActionType(is_unirxn=False))
        first = FakeAction("first", FakeActionType(is_unirxn=False))
        unirxn = FakeAction("uni", FakeActionType(is_unirxn=True))
        routes = [
            [(observed, "parent"), (first, "")],
            [(other, "alternative"), (unirxn, "middle"), (first, "")],
        ]
        value = MODULE.backward_log_probability(observed, routes, "parent", 100.0)
        self.assertAlmostEqual(value, -0.6931471805599453)

    def test_backward_probability_rejects_a_missing_generated_route(self):
        observed = FakeAction("observed", FakeActionType(is_unirxn=False))
        route = [[(FakeAction("other", FakeActionType(False)), "parent")]]
        with self.assertRaisesRegex(ValueError, "lost the generated route"):
            MODULE.backward_log_probability(observed, route, "parent", 100.0)

    def test_membership_loader_requires_a_passing_unique_bank(self):
        payload = {
            "qualification": "pass",
            "bank_size": 2,
            "construction_memberships": {"graph": ["a", "b"]},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qualification.json"
            path.write_text(json.dumps(payload))
            record_ids, loaded = MODULE.load_memberships(path, "graph")
        self.assertEqual(record_ids, ["a", "b"])
        self.assertEqual(loaded, payload)

    def test_membership_loader_accepts_an_outcome_sealed_prospective_bank(self):
        payload = {
            "qualification": "pass",
            "outcomes_opened": False,
            "banks": {"graph_aware_hybrid": {"members": ["a", "b"]}},
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "qualification.json"
            path.write_text(json.dumps(payload))
            record_ids, loaded = MODULE.load_memberships(path, "graph_aware_hybrid")
        self.assertEqual(record_ids, ["a", "b"])
        self.assertEqual(loaded, payload)

    def test_load_requires_a_fresh_trainer_and_disables_online_insertion(self):
        items = [{"final_smiles": "C", "anarres_record_id": "record-a"}]
        artifact = {
            "artifact_type": MODULE.ARTIFACT_TYPE,
            "item_count": 1,
            "items_sha256": MODULE.canonical_json_sha256(items),
            "items": items,
        }
        replay = FakeReplay()
        trainer = SimpleNamespace(
            step=0,
            replay=replay,
            config=SimpleNamespace(training=SimpleNamespace(num_replay_insert=0)),
        )
        MODULE.load_into_fresh_replay(trainer, artifact)
        self.assertEqual(replay.state["capacity"], replay.capacity)
        self.assertEqual(replay.state["items"], [{"final_smiles": "C"}])

        trainer.replay = FakeReplay()
        trainer.config.training.num_replay_insert = 1
        with self.assertRaisesRegex(ValueError, "insertion must be disabled"):
            MODULE.load_into_fresh_replay(trainer, artifact)

    def test_load_rejects_a_modified_artifact(self):
        artifact = {
            "artifact_type": MODULE.ARTIFACT_TYPE,
            "item_count": 1,
            "items_sha256": "0" * 64,
            "items": [{"final_smiles": "C"}],
        }
        trainer = SimpleNamespace(
            step=0,
            replay=FakeReplay(),
            config=SimpleNamespace(training=SimpleNamespace(num_replay_insert=0)),
        )
        with self.assertRaisesRegex(ValueError, "digest is inconsistent"):
            MODULE.load_into_fresh_replay(trainer, artifact)


if __name__ == "__main__":
    unittest.main()
