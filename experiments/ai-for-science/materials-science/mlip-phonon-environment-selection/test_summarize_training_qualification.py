import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("summarize_training_qualification.py")
SPEC = importlib.util.spec_from_file_location("summarize_training_qualification", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_evaluation(path, model, loss):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "dataset_sha256": "d" * 64,
                "model_sha256": model,
                "records": {"total": 100, "training": 95, "validation": 5},
                "split": {"validation_fraction": 0.05, "validation_seed": 42},
                "loss_contract": {"loss_type": "mae"},
                "metrics": {
                    "loss": loss,
                    "force_mae": loss / 40,
                    "stress_mae_per_atom": 0.01,
                },
            }
        ),
        encoding="utf-8",
    )


def test_frozen_rule_selects_largest_passing_learning_rate(tmp_path):
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "qualification_environment": {"candidate_id": "discarded"},
                "starting_checkpoint": {"sha256": "b" * 64},
                "qualification_grid": {
                    "learning_rates": [1e-5, 3e-5, 1e-4],
                    "selection_rule": "largest passing",
                },
            }
        ),
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.json"
    write_evaluation(baseline, "b" * 64, 5.0)
    for learning_rate, loss in ((1e-5, 4.9), (3e-5, 4.7), (1e-4, 4.8)):
        run = tmp_path / MODULE.learning_rate_label(learning_rate)
        write_evaluation(run / "reloaded_efs.json", "c" * 64, loss)
        (run / "checkpoints").mkdir()
        (run / "checkpoints" / "epoch_0001.nqx").write_bytes(b"checkpoint")
        (run / "train_rerun.log").write_text("logs: {'train/grad_norm': 2.5}\n", encoding="utf-8")
    result = MODULE.summarize(protocol, baseline, tmp_path)
    assert result["selected_learning_rate"] == 1e-4
    assert all(run["passed"] for run in result["runs"])


def test_nonfinite_gradient_rejects_run(tmp_path):
    log = tmp_path / "train.log"
    log.write_text("logs: {'train/grad_norm': nan}\n", encoding="utf-8")
    try:
        MODULE.gradient_summary(log)
    except ValueError as error:
        assert "finite gradient" in str(error)
    else:
        raise AssertionError("non-finite gradient was accepted")
