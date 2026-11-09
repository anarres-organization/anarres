import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).parent / "scripts" / "ingest_wong_yang_2026.py"
SPEC = importlib.util.spec_from_file_location("ingest_wong_yang_2026", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_reconstruct_joins_measurements_and_normalizes_energy(tmp_path):
    arms = []
    probes = []
    for budget in (10, 21, 31, 40, 50):
        for environment, energy in (("naive", 2.0), ("periodic", 1.0)):
            panel = f"wong_yang_2026_umlip_bias:budget_{budget}"
            arms.append(
                {
                    "panel_id": panel,
                    "environment": environment,
                    "training_configuration_count": budget,
                    "model_relative_path": f"{environment}.model",
                    "model_sha256": environment * 8,
                    "outcome": {"energy_mae_meV_per_atom": energy},
                }
            )
            probes.append(
                {
                    "panel_id": panel,
                    "environment": environment,
                    "training_configuration_count": budget,
                    "dataset_relative_path": f"{environment}.xyz",
                    "dataset_sha256": environment * 8,
                    "measurements": {"effective_configuration_coverage": 0.5},
                }
            )
    evaluation = tmp_path / "evaluation.json"
    measurement = tmp_path / "measurement.json"
    evaluation.write_text(
        json.dumps(
            {
                "source_revision": "revision",
                "test_contract": {"structure_count": 22},
                "arms": arms,
            }
        )
    )
    measurement.write_text(
        json.dumps(
            {
                "source_revision": "revision",
                "starting_model_sha256": "start",
                "arms": probes,
            }
        )
    )
    payload = MODULE.reconstruct(evaluation, measurement)
    assert payload["panel_count"] == 5
    assert payload["arm_count"] == 10
    periodic = [arm for arm in payload["arms"] if arm["environment"] == "periodic"]
    assert all(arm["derived"]["panel_normalized_utility"] == 1 for arm in periodic)
