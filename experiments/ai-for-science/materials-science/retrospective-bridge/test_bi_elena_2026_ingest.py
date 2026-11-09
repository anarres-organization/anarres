import csv
import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "ingest_bi_elena_2026.py"
SPEC = importlib.util.spec_from_file_location("ingest_bi_elena_2026", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_reconstructs_complete_budget_endpoint_panels(tmp_path):
    source = tmp_path / "source.csv"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "dataset",
                "selector",
                "budget_fraction",
                "endpoint",
                "gap_pct",
                "seed_aggregation",
            ),
        )
        writer.writeheader()
        for dataset in ("Carbon", "rMD17 full"):
            for budget in (0.01, 0.05, 0.2):
                for endpoint in ("mean", "stratum", "tail", "novelty"):
                    for index, selector in enumerate(MODULE.SELECTORS):
                        writer.writerow(
                            {
                                "dataset": dataset,
                                "selector": selector,
                                "budget_fraction": budget,
                                "endpoint": endpoint,
                                "gap_pct": index + 1,
                                "seed_aggregation": "mean_of_seeds_1_to_5",
                            }
                        )
    payload = MODULE.reconstruct(source)
    assert payload["panel_count"] == 24
    assert payload["arm_count"] == 120
    best = [arm for arm in payload["arms"] if arm["selector"] == "Random"]
    assert all(arm["derived"]["panel_normalized_utility"] == 1 for arm in best)
