from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "smoke_replay_training.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("smoke_replay_training", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_configure_smoke_uses_requested_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        env_dir=None,
        training=SimpleNamespace(
            log_every=10,
            checkpoint_every=200,
            num_online=2,
            num_replay=2,
            replay_capacity=512,
            num_replay_insert=0,
        ),
    )

    class Config:
        @staticmethod
        def from_file(path: Path) -> SimpleNamespace:
            assert path == Path("config.yaml")
            return config

    monkeypatch.setitem(sys.modules, "rxnflow.config", SimpleNamespace(Config=Config))
    observed = MODULE.configure_smoke(
        Path("config.yaml"), Path("env"), num_online=64, num_replay=64
    )
    assert observed.training.num_online == 64
    assert observed.training.num_replay == 64
    assert observed.training.num_replay_insert == 0


def test_configure_smoke_rejects_empty_batch() -> None:
    with pytest.raises(ValueError, match="positive"):
        MODULE.configure_smoke(Path("config.yaml"), Path("env"), num_online=0, num_replay=64)
