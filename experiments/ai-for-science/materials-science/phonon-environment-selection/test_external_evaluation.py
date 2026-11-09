import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_script(name):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCORING = load_script("score_external_predictions.py")
COMPOSITION = load_script("audit_candidate_composition.py")
SUMMARY = load_script("summarize_external_results.py")


class ExternalEvaluationTest(unittest.TestCase):
    def test_auc_and_concordance(self):
        self.assertEqual(SCORING.auc([False, False, True, True], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertEqual(SCORING.auc([False, True], [0.5, 0.5]), 0.5)
        self.assertEqual(SCORING.concordance([0.0, 1.0, 2.0], [0.0, 1.0, 2.0]), 1.0)
        self.assertEqual(SCORING.concordance([0.0, 1.0], [1.0, 0.0]), 0.0)

    def test_label_blind_materialization_extracts_only_cifs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "source.zip"
            prefixes = {
                "dft_pbe": "root/test_dft_pbe",
                "mp20": "root/test_mp20",
            }
            with zipfile.ZipFile(archive, "w") as handle:
                for panel, prefix in prefixes.items():
                    handle.writestr(f"{prefix}/cifs/000001.cif", f"data_{panel}")
                    handle.writestr(f"{prefix}/manifest.json", '[{"secret_label": 1}]')
                    handle.writestr(f"{prefix}/id_prop.csv", "secret,label\n")
            contract = {
                "source_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "external_test_labels_inspected_at_freeze": False,
                "panels": {
                    panel: {"archive_prefix": prefix, "records": 1}
                    for panel, prefix in prefixes.items()
                },
            }
            contract_path = root / "contract.json"
            contract_path.write_text(json.dumps(contract))
            output = root / "inputs"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "prepare_external_inputs.py"),
                    "--archive",
                    str(archive),
                    "--contract",
                    str(contract_path),
                    "--out",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue((output / "dft_pbe" / "cifs" / "000001.cif").is_file())
            self.assertTrue((output / "mp20" / "cifs" / "000001.cif").is_file())
            self.assertFalse(
                any(path.name in {"manifest.json", "id_prop.csv"} for path in output.rglob("*"))
            )
            manifest = json.loads((output / "INPUT_MANIFEST.json").read_text())
            self.assertFalse(manifest["external_labels_read"])
            self.assertEqual(len(manifest["records"]), 2)

    def test_metric_bundle(self):
        rows = []
        for index, target in enumerate([-1.0, -0.2, 0.0, 0.2]):
            rows.append(
                {
                    "local_id": str(index),
                    "min_frequency": target,
                    "composite_score": target,
                    "threshold_probability_minus_0p1": 0.9 if target > -0.1 else 0.1,
                    "prediction": target,
                }
            )
        metrics = SCORING.evaluate(rows, 2)
        self.assertEqual(metrics["top_k_stable_rate"], 1.0)
        self.assertEqual(metrics["continuous_pairwise_concordance"], 1.0)
        self.assertEqual(metrics["roc_auc"], 1.0)
        self.assertAlmostEqual(metrics["brier_score"], 0.01)
        self.assertEqual(metrics["minimum_frequency_mae_thz"], 0.0)

    def test_composition_quantile_interpolates(self):
        self.assertEqual(COMPOSITION.quantile([0.0, 10.0], 0.25), 2.5)
        self.assertEqual(COMPOSITION.quantile([3.0], 0.95), 3.0)

    def test_summary_aggregate_preserves_replicates(self):
        rows = [
            {"candidate": "a", **{metric: 1.0 for metric in SUMMARY.METRICS}},
            {"candidate": "a", **{metric: 3.0 for metric in SUMMARY.METRICS}},
        ]
        result = SUMMARY.aggregate(rows, ("candidate",))
        self.assertEqual(result[0]["replicates"], 2)
        for metric in SUMMARY.METRICS:
            self.assertEqual(result[0][metric], 2.0)


if __name__ == "__main__":
    unittest.main()
