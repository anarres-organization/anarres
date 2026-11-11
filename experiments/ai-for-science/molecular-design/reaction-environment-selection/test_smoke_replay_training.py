from __future__ import annotations

import importlib.util
import json
import subprocess
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


def test_inspect_oracle_python_records_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "python"
    executable.write_bytes(b"python")

    def run(command, **_kwargs):
        assert command[0] == str(executable)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"meeko": "1", "openbabel": "2", "rdkit": "3", "vina": "4"}),
            "",
        )

    monkeypatch.setattr(MODULE.subprocess, "run", run)
    identity = MODULE.inspect_oracle_python(executable)
    assert identity["packages"]["vina"] == "4"
    assert identity["executable_sha256"] == MODULE.sha256_file(executable)


def test_released_full_batch_cpu_smoke_preserves_interface_boundary() -> None:
    report = json.loads((ROOT / "FULL_BATCH_CPU_TRAINING_SMOKE_V1.json").read_text())
    assert report["status"] == "pass"
    assert report["execution"]["device"] == "cpu"
    assert report["smoke_batch"] == {"online": 64, "replay": 64, "updates": 1}
    assert all(report["checks"].values())
    assert "not a target-training outcome" in report["claim_boundary"]
