import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "reaction_protocol", ROOT / "scripts" / "validate_protocol.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load() -> tuple[dict[str, object], dict[str, object]]:
    return (
        json.loads((ROOT / "PROTOCOL.json").read_text(encoding="utf-8")),
        json.loads((ROOT / "SOURCES.json").read_text(encoding="utf-8")),
    )


def test_committed_protocol_is_valid() -> None:
    protocol, sources = load()
    assert MODULE.validate(protocol, sources) == []


def test_outcomes_cannot_be_open_at_qualification() -> None:
    protocol, sources = load()
    protocol["sealed_boundary"]["training_or_evaluation_outcomes_inspected"] = True
    errors = MODULE.validate(protocol, sources)
    assert "outcomes must remain uninspected at this stage" in errors


def test_only_experience_bank_can_vary() -> None:
    protocol, sources = load()
    protocol["intervention"]["only_arm_specific_input"] = "reaction catalog"
    errors = MODULE.validate(protocol, sources)
    assert "experience-bank membership must be the only arm-specific input" in errors


def test_qed_replay_state_cannot_enter_target_training() -> None:
    protocol, sources = load()
    protocol["starting_policy"]["qed_optimizer_or_replay_state_reused"] = True
    errors = MODULE.validate(protocol, sources)
    assert "QED optimizer and replay state cannot enter target training" in errors


def test_online_trajectories_cannot_replace_frozen_bank() -> None:
    protocol, sources = load()
    protocol["intervention"]["rxnflow_num_replay_insert"] = 64
    errors = MODULE.validate(protocol, sources)
    assert "online trajectories cannot replace the frozen replay bank" in errors
