#!/usr/bin/env python3
"""Measure matched uMLIP environments under their common starting potential."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


DATASETS = {
    10: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-10pts/10pt_dataset_raw.xyz",
        "data/ChClCA_Finetuning/Periodic/Model:FT1/model/u_data_raw.xyz",
    ),
    21: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-21pts/21pt_dataset_raw.xyz",
        "data/ChClCA_Finetuning/Periodic/Model:FT2/model/ft1_data_raw.xyz",
    ),
    31: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-31pts/31pt_dataset_raw.xyz",
        "data/ChClCA_Finetuning/Periodic/Model:FT3/model/ft2_data_raw.xyz",
    ),
    40: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-40pts/40pt_dataset_raw.xyz",
        "data/ChClCA_Finetuning/Periodic/Model:FT4/model/ft3_data_raw.xyz",
    ),
    50: (
        "data/ChClCA_Finetuning/Naive/Finetuned_Models/N-50pts/ft_dataset_raw.xyz",
        "data/ChClCA_Finetuning/Periodic/Model:FT5/model/ft4_data_raw.xyz",
    ),
}
START_MODEL = "data/ChClCA_Finetuning/Periodic/Model:U/model/mace_agnesi_small.model"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def effective_coverage(masses: np.ndarray) -> float:
    masses = np.asarray(masses, dtype=float)
    total = float(masses.sum())
    if total == 0 or len(masses) == 0:
        return 0.0
    return float(total**2 / (len(masses) * np.sum(masses**2)))


def atom_fingerprint(atoms) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(atoms.numbers, dtype=np.int16).tobytes())
    digest.update(np.round(atoms.positions, 8).astype(np.float64).tobytes())
    digest.update(np.round(atoms.cell.array, 8).astype(np.float64).tobytes())
    digest.update(np.asarray([atoms.get_potential_energy()], dtype=np.float64).tobytes())
    available = set() if atoms.calc is None else set(atoms.calc.results)
    if "forces" in available:
        digest.update(b"forces-present")
        digest.update(np.asarray(atoms.get_forces(), dtype=np.float64).tobytes())
    else:
        digest.update(b"forces-absent")
    return digest.hexdigest()


def summarize(rows: list[dict]) -> dict:
    energy_errors = np.asarray([row["energy_error_meV_per_atom"] for row in rows])
    energy_masses = np.abs(energy_errors)
    force_rows = [row for row in rows if row["force_error_norms_eV_per_A"] is not None]
    force_masses = np.asarray([row["force_error_mass_eV_per_A"] for row in force_rows])
    atom_errors = (
        np.concatenate([np.asarray(row["force_error_norms_eV_per_A"]) for row in force_rows])
        if force_rows
        else np.asarray([])
    )
    result = {
        "configuration_count": len(rows),
        "atom_count": int(sum(row["atom_count"] for row in rows)),
        "starting_energy_mae_meV_per_atom": float(np.mean(np.abs(energy_errors))),
        "starting_energy_rmse_meV_per_atom": float(np.sqrt(np.mean(energy_errors**2))),
        "effective_configuration_coverage_energy_error": effective_coverage(energy_masses),
        "force_labeled_configuration_count": len(force_rows),
        "force_labeled_atom_count": int(sum(row["atom_count"] for row in force_rows)),
    }
    if force_rows:
        result |= {
            "starting_force_error_density_eV_per_A_per_atom": float(
                force_masses.sum() / sum(row["atom_count"] for row in force_rows)
            ),
            "starting_force_vector_rmse_eV_per_A": float(np.sqrt(np.mean(atom_errors**2))),
            "starting_force_error_p90_eV_per_A": float(np.quantile(atom_errors, 0.9)),
            "effective_configuration_coverage_force_error": effective_coverage(force_masses),
            "effective_atom_coverage_force_error": effective_coverage(atom_errors),
        }
    else:
        result |= {
            "starting_force_error_density_eV_per_A_per_atom": None,
            "starting_force_vector_rmse_eV_per_A": None,
            "starting_force_error_p90_eV_per_A": None,
            "effective_configuration_coverage_force_error": None,
            "effective_atom_coverage_force_error": None,
        }
    return result


def measure(repository: Path, output: Path, device: str) -> dict:
    from ase.io import read
    from mace.calculators import MACECalculator

    model_path = repository / START_MODEL
    calculator = MACECalculator(model_paths=str(model_path), device=device)
    cache: dict[str, dict] = {}
    arms = []
    for budget, (naive_relative, periodic_relative) in DATASETS.items():
        for environment, relative in (("naive", naive_relative), ("periodic", periodic_relative)):
            dataset_path = repository / relative
            structures = read(dataset_path, index=":")
            rows = []
            for atoms in structures:
                fingerprint = atom_fingerprint(atoms)
                if fingerprint not in cache:
                    reference_energy = float(atoms.get_potential_energy())
                    available = set() if atoms.calc is None else set(atoms.calc.results)
                    reference_forces = (
                        np.asarray(atoms.get_forces(), dtype=float)
                        if "forces" in available
                        else None
                    )
                    evaluated = atoms.copy()
                    evaluated.calc = calculator
                    predicted_energy = float(evaluated.get_potential_energy())
                    if reference_forces is not None:
                        predicted_forces = np.asarray(evaluated.get_forces(), dtype=float)
                        force_norms = np.linalg.norm(predicted_forces - reference_forces, axis=1)
                        force_mass = float(force_norms.sum())
                        force_norm_list = force_norms.tolist()
                    else:
                        force_mass = None
                        force_norm_list = None
                    cache[fingerprint] = {
                        "atom_count": len(atoms),
                        "energy_error_meV_per_atom": 1000
                        * (predicted_energy - reference_energy)
                        / len(atoms),
                        "force_error_mass_eV_per_A": force_mass,
                        "force_error_norms_eV_per_A": force_norm_list,
                    }
                rows.append(cache[fingerprint])
            arms.append(
                {
                    "panel_id": f"wong_yang_2026_umlip_bias:budget_{budget}",
                    "environment": environment,
                    "training_configuration_count": budget,
                    "dataset_relative_path": relative,
                    "dataset_sha256": sha256(dataset_path),
                    "measurements": summarize(rows),
                }
            )
    payload = {
        "artifact": "wong_yang_2026_starting_model_measurements_v1",
        "source_revision": "de86171359689e7240d074e80d7f0ecb7b0394a4",
        "device": device,
        "starting_model_relative_path": START_MODEL,
        "starting_model_sha256": sha256(model_path),
        "unique_configuration_count": len(cache),
        "panel_count": len(DATASETS),
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
    payload = measure(args.repository, args.out, args.device)
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
