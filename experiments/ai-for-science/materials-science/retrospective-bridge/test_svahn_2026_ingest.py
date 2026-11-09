import csv
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "ingest_svahn_2026.py"
SPEC = importlib.util.spec_from_file_location("svahn_ingest", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reconstructs_only_matched_random_subset_panels(tmp_path):
    source = tmp_path / "source.csv"
    fields = [
        "Data set", "Labels", "Seed ID", "Sample ID", "Composition",
        "Temperature /K", "Density /g*cm-3",
        "Diff. coeff. /1e6 cm2*s-1",
    ]
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for budget in ("Clusters-Small", "Clusters-Medium"):
            for composition, temperature in (("EC", 313), ("EMC", 298)):
                for sample in (1, 2, 3):
                    writer.writerow({
                        "Data set": budget,
                        "Labels": "wB97X-D3",
                        "Seed ID": 1,
                        "Sample ID": sample,
                        "Composition": composition,
                        "Temperature /K": temperature,
                        "Density /g*cm-3": 1.0 + sample / 100,
                        "Diff. coeff. /1e6 cm2*s-1": 5.0 + sample,
                    })
    payload = MODULE.reconstruct(source)
    assert payload["panel_count"] == 8
    assert payload["arm_count"] == 24
    assert payload["role"] == "uncertainty audit; excluded from predictive fitting"
    assert all(
        arm["pre_outcome_measurements"]["distinguishing_measurement_available"] == 0
        for arm in payload["arms"]
    )
