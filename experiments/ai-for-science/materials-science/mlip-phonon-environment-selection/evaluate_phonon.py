#!/usr/bin/env python3
"""Evaluate one MLIP checkpoint with the released Alexandria phonon workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import phonopy
from ase import Atoms
from ase.constraints import FixSymmetry
from ase.filters import FrechetCellFilter
from ase.optimize import FIRE
from phonopy.harmonic.dynmat_to_fc import get_commensurate_points


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atoms_from_phonopy(structure) -> Atoms:
    return Atoms(
        cell=structure.cell,
        symbols=structure.symbols,
        scaled_positions=structure.scaled_positions,
        pbc=True,
    )


def relax_unitcell(atoms: Atoms, calculator, fmax: float, max_steps: int) -> tuple[Atoms, dict]:
    relaxed = atoms.copy()
    relaxed.calc = calculator
    relaxed.set_constraint(FixSymmetry(relaxed))
    filtered = FrechetCellFilter(relaxed)
    started = time.perf_counter()
    optimizer = FIRE(filtered, logfile=None)
    converged = bool(optimizer.run(fmax=fmax / 2, steps=max_steps))
    relaxed = filtered.atoms
    relaxed.set_constraint()
    relaxed.calc = calculator
    force_max = float(np.linalg.norm(relaxed.get_forces(), axis=1).max())
    return relaxed, {
        "converged": converged and force_max <= fmax,
        "optimizer_steps": int(optimizer.nsteps),
        "force_max_ev_per_angstrom": force_max,
        "seconds": time.perf_counter() - started,
    }


def calculate_phonons(reference, atoms: Atoms, calculator, distance: float) -> tuple[object, dict]:
    ph_atoms = phonopy.structure.atoms.PhonopyAtoms(
        cell=atoms.cell,
        symbols=atoms.get_chemical_symbols(),
        scaled_positions=atoms.get_scaled_positions(),
    )
    predicted = phonopy.Phonopy(
        ph_atoms,
        supercell_matrix=reference.supercell_matrix,
        primitive_matrix=reference.primitive_matrix,
    )
    predicted.generate_displacements(distance=distance, is_diagonal=False)
    forcesets = []
    started = time.perf_counter()
    for supercell in predicted.supercells_with_displacements:
        displaced = atoms_from_phonopy(supercell)
        displaced.calc = calculator
        forces = displaced.get_forces()
        forces = forces - forces.mean(axis=0, keepdims=True)
        forcesets.append(forces)
    predicted.forces = forcesets
    predicted.produce_force_constants()
    predicted.symmetrize_force_constants()
    return predicted, {
        "displacements": len(forcesets),
        "supercell_atoms": len(predicted.supercell),
        "seconds": time.perf_counter() - started,
    }


def commensurate_frequencies(phonon) -> np.ndarray:
    qpoints = get_commensurate_points(phonon.supercell_matrix)
    values = np.asarray([np.sort(phonon.get_frequencies(qpoint)) for qpoint in qpoints])
    return values


def is_stable(frequencies_thz: np.ndarray) -> bool:
    """Use the released benchmark's stability rule, converted from kelvin to THz."""
    frequencies_kelvin = frequencies_thz * 47.992
    gamma = frequencies_kelvin[0]
    return not (
        np.any(gamma[:3] < -35.0)
        or np.any(gamma[3:] < 0.0)
        or np.any(frequencies_kelvin[1:] < 0.0)
    )


def load_calculator(backend: str, model_path: Path):
    if backend == "nequix":
        from nequix.calculator import NequixCalculator

        return NequixCalculator(
            model_name="nequix-mp-1",
            model_path=str(model_path),
            backend="jax",
            use_kernel=False,
        )
    if backend == "mace":
        from mace.calculators import MACECalculator

        return MACECalculator(model_paths=str(model_path), device="cuda")
    raise ValueError(f"unsupported backend: {backend}")


def evaluate(
    yaml_path: Path,
    model_path: Path,
    backend: str,
    distance: float,
    fmax: float,
    max_steps: int,
) -> dict:
    started = time.perf_counter()
    reference = phonopy.load(yaml_path)
    reference.produce_force_constants()
    starting_atoms = atoms_from_phonopy(reference.unitcell)

    load_started = time.perf_counter()
    calculator = load_calculator(backend, model_path)
    model_load_seconds = time.perf_counter() - load_started

    relaxed, relaxation = relax_unitcell(starting_atoms, calculator, fmax, max_steps)
    predicted, force_set = calculate_phonons(reference, relaxed, calculator, distance)
    reference_frequencies = commensurate_frequencies(reference)
    predicted_frequencies = commensurate_frequencies(predicted)
    assert reference_frequencies.shape == predicted_frequencies.shape
    error = predicted_frequencies - reference_frequencies

    return {
        "artifact": "anarres_mlip_phonon_evaluation_v1",
        "material_id": yaml_path.name.removesuffix(".yaml.bz2"),
        "backend": backend,
        "model_sha256": sha256(model_path),
        "workflow": {
            "distance_angstrom": distance,
            "relaxation_fmax_ev_per_angstrom": fmax,
            "relaxation_max_steps": max_steps,
            "net_force_drift_removed": True,
            "force_constants_symmetrized": True,
        },
        "structure": {
            "unitcell_atoms": len(starting_atoms),
            "reference_supercell_atoms": len(reference.supercell),
            "volume_change_fraction": float(relaxed.get_volume() / starting_atoms.get_volume() - 1),
        },
        "relaxation": relaxation,
        "force_set": force_set,
        "metrics": {
            "frequency_mae_thz": float(np.mean(np.abs(error))),
            "frequency_rmse_thz": float(np.sqrt(np.mean(error ** 2))),
            "maximum_frequency_error_thz": float(
                np.max(predicted_frequencies) - np.max(reference_frequencies)
            ),
            "reference_stable": is_stable(reference_frequencies),
            "predicted_stable": is_stable(predicted_frequencies),
            "commensurate_qpoints": int(reference_frequencies.shape[0]),
            "modes_per_qpoint": int(reference_frequencies.shape[1]),
        },
        "timing_seconds": {
            "model_load": model_load_seconds,
            "total": time.perf_counter() - started,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--backend", choices=["nequix", "mace"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--distance", type=float, default=0.01)
    parser.add_argument("--fmax", type=float, default=0.005)
    parser.add_argument("--max-steps", type=int, default=500)
    args = parser.parse_args()
    result = evaluate(
        args.yaml,
        args.model,
        args.backend,
        args.distance,
        args.fmax,
        args.max_steps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
