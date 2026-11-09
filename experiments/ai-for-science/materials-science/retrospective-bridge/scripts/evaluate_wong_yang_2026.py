#!/usr/bin/env python3
"""Evaluate released matched-budget uMLIP checkpoints on one common DFT test set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


BUDGET_MODELS = {
    10: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-10pts/10pts.model",
        "data/ChClCA_Finetuning/Periodic/Model:FT1/model/ft1.model",
    ),
    21: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-21pts/21pts.model",
        "data/ChClCA_Finetuning/Periodic/Model:FT2/model/ft2.model",
    ),
    31: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-31pts/31pts.model",
        "data/ChClCA_Finetuning/Periodic/Model:FT3/model/ft3.model",
    ),
    40: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-40pts/40pts.model",
        "data/ChClCA_Finetuning/Periodic/Model:FT4/model/ft4.model",
    ),
    50: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-50pts/50pts.model",
        "data/ChClCA_Finetuning/Periodic/Model:FT5/model/ft5.model",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def summarize_predictions(records: list[dict]) -> dict:
    energy_errors = np.asarray([row["energy_error_meV_per_atom"] for row in records])
    force_errors = np.concatenate(
        [np.asarray(row["force_error_eV_per_A"], dtype=float).reshape(-1, 3) for row in records],
        axis=0,
    )
    force_component_errors = force_errors.reshape(-1)
    force_vector_errors = np.linalg.norm(force_errors, axis=1)
    return {
        "structure_count": len(records),
        "atom_count": int(sum(row["atom_count"] for row in records)),
        "energy_mae_meV_per_atom": float(np.mean(np.abs(energy_errors))),
        "energy_rmse_meV_per_atom": float(np.sqrt(np.mean(energy_errors**2))),
        "energy_bias_meV_per_atom": float(np.mean(energy_errors)),
        "force_component_mae_eV_per_A": float(np.mean(np.abs(force_component_errors))),
        "force_component_rmse_eV_per_A": float(
            np.sqrt(np.mean(force_component_errors**2))
        ),
        "force_vector_mae_eV_per_A": float(np.mean(force_vector_errors)),
        "force_vector_rmse_eV_per_A": float(np.sqrt(np.mean(force_vector_errors**2))),
    }


def load_test_set(test_root: Path):
    from ase.io import read

    rows = []
    for metadata_path in sorted(
        test_root.glob("eval.*/vasp_info.json"),
        key=lambda path: int(path.parent.name.split(".")[-1]),
    ):
        eval_id = int(metadata_path.parent.name.split(".")[-1])
        atoms = read(metadata_path.parent / "POSCAR")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        reference_forces = np.asarray(metadata["forces"], dtype=float)
        if reference_forces.shape != (len(atoms), 3):
            raise ValueError(f"force shape mismatch for eval.{eval_id}")
        rows.append(
            {
                "eval_id": eval_id,
                "atoms": atoms,
                "reference_energy_eV": float(metadata["energy"]),
                "reference_forces_eV_per_A": reference_forces,
                "poscar_sha256": sha256(metadata_path.parent / "POSCAR"),
                "metadata_sha256": sha256(metadata_path),
            }
        )
    if len(rows) != 22:
        raise ValueError(f"expected 22 independent test structures, found {len(rows)}")
    return rows


def evaluate_model(model_path: Path, test_rows: list[dict], device: str) -> tuple[dict, list[dict]]:
    from mace.calculators import MACECalculator

    calculator = MACECalculator(model_paths=str(model_path), device=device)
    predictions = []
    for row in test_rows:
        atoms = row["atoms"].copy()
        atoms.calc = calculator
        predicted_energy = float(atoms.get_potential_energy())
        predicted_forces = np.asarray(atoms.get_forces(), dtype=float)
        energy_error = 1000 * (predicted_energy - row["reference_energy_eV"]) / len(atoms)
        force_error = predicted_forces - row["reference_forces_eV_per_A"]
        predictions.append(
            {
                "eval_id": row["eval_id"],
                "atom_count": len(atoms),
                "energy_error_meV_per_atom": energy_error,
                "force_error_eV_per_A": force_error.tolist(),
            }
        )
    return summarize_predictions(predictions), predictions


def evaluate(repository: Path, output: Path, device: str) -> dict:
    test_root = repository / "data/ChClCA_Evaluations/Independent_Test_Set"
    test_rows = load_test_set(test_root)
    arms = []
    for budget, (naive_relative, periodic_relative) in BUDGET_MODELS.items():
        for environment, relative in (("naive", naive_relative), ("periodic", periodic_relative)):
            model_path = repository / relative
            if not model_path.is_file():
                raise FileNotFoundError(model_path)
            metrics, predictions = evaluate_model(model_path, test_rows, device)
            arms.append(
                {
                    "panel_id": f"wong_yang_2026_umlip_bias:budget_{budget}",
                    "environment": environment,
                    "training_configuration_count": budget,
                    "model_relative_path": relative,
                    "model_sha256": sha256(model_path),
                    "outcome": metrics,
                    "per_structure": predictions,
                }
            )

    payload = {
        "artifact": "wong_yang_2026_common_test_evaluation_v1",
        "source_revision": "de86171359689e7240d074e80d7f0ecb7b0394a4",
        "device": device,
        "test_contract": {
            "relative_path": "data/ChClCA_Evaluations/Independent_Test_Set",
            "structure_count": len(test_rows),
            "atom_count": sum(len(row["atoms"]) for row in test_rows),
            "test_files": [
                {
                    "eval_id": row["eval_id"],
                    "poscar_sha256": row["poscar_sha256"],
                    "metadata_sha256": row["metadata_sha256"],
                }
                for row in test_rows
            ],
        },
        "panel_count": len(BUDGET_MODELS),
        "arm_count": len(arms),
        "arms": arms,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    payload = evaluate(args.repository, args.out, args.device)
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
