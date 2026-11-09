import csv
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "ingest_li_2023.py"
SPEC = importlib.util.spec_from_file_location("li_ingest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _write(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_reconstructs_matched_panels(tmp_path):
    active = tmp_path / "performance_on_ID_data" / "active_learning"
    random = tmp_path / "performance_on_ID_data" / "random_sampling"
    active_fields = ["train_ratio", "maes", "rmse", "r2", "train_size"]
    random_fields = ["train_size", "maes", "maes_std", "rmse", "rmse_std", "r2", "r2_std"]
    for method, errors in {
        "QBC": (0.8, 0.6, 0.5),
        "rfMaxUncertainty": (0.7, 0.5, 0.4),
        "xgbMaxUncertainty": (0.9, 0.7, 0.6),
    }.items():
        _write(
            active / f"bandgap_mp_rf_{method}.csv",
            active_fields,
            [
                {
                    "train_ratio": budget,
                    "maes": error / 2,
                    "rmse": error,
                    "r2": 0.5,
                    "train_size": 10,
                }
                for budget, error in zip((0.02, 0.10, 0.20), errors, strict=False)
            ],
        )
    _write(
        random / "bandgap_mp_rf_rand.csv",
        random_fields,
        [
            {
                "train_size": budget,
                "maes": error / 2,
                "maes_std": 0.01,
                "rmse": error,
                "rmse_std": 0.02,
                "r2": 0.4,
                "r2_std": 0.03,
            }
            for budget, error in zip((0.02, 0.10, 0.20), (1.0, 0.8, 0.7), strict=False)
        ],
    )

    payload = MODULE.reconstruct(tmp_path)
    assert payload["panel_count"] == 3
    assert payload["arm_count"] == 12
    first_panel = [arm for arm in payload["arms"] if arm["requested_pool_fraction"] == 0.02]
    best = max(first_panel, key=lambda arm: arm["derived"]["panel_normalized_utility"])
    assert best["method"] == "rfMaxUncertainty"
    assert best["derived"]["panel_normalized_utility"] == 1.0
    random_arm = next(arm for arm in first_panel if arm["method"] == "random")
    assert random_arm["outcome"]["rmse_std"] == 0.02
