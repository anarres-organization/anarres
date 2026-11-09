import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "summarize_checkpoint_qualification.py"
SPEC = importlib.util.spec_from_file_location("summarize_checkpoint_qualification", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def result(mae, accuracy, runtime, eligible=True):
    return {
        "eligible": eligible,
        "frequency_mae_thz": {"mean": mae},
        "stability_accuracy": accuracy,
        "evaluation_runtime_excluding_model_load_seconds": {"median": runtime},
    }


def test_selects_materially_lower_frequency_error():
    selected, _ = MODULE.select_backend(
        {
            "mace": result(0.20, 1.0, 5.0),
            "nequix": result(0.15, 0.8, 10.0),
        }
    )
    assert selected == "nequix"


def test_uses_tie_breakers_inside_equivalence_band():
    selected, _ = MODULE.select_backend(
        {
            "mace": result(0.20, 1.0, 5.0),
            "nequix": result(0.195, 0.9, 4.0),
        }
    )
    assert selected == "mace"


def test_rejects_ineligible_checkpoint():
    selected, _ = MODULE.select_backend(
        {
            "mace": result(0.20, 1.0, 5.0, eligible=False),
            "nequix": result(0.25, 0.8, 10.0),
        }
    )
    assert selected == "nequix"
