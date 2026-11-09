#!/usr/bin/env python3
"""Qualify the frozen MolGenBench docking fixtures without reading outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

DEFAULT_SEEDS = (20261108, 20261109)
DEFAULT_REPEATS = 2
DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_BUFFER_ANGSTROM = 5.0
MAX_REPEAT_DELTA = 1e-6
MAX_CROSS_SEED_RANGE = 2.0
MAX_REFERENCE_AFFINITY = -4.0


@dataclass(frozen=True)
class GateContract:
    """Prespecified pass criteria for a target docking fixture."""

    max_repeat_delta: float = MAX_REPEAT_DELTA
    max_cross_seed_range: float = MAX_CROSS_SEED_RANGE
    max_reference_affinity: float = MAX_REFERENCE_AFFINITY


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def target_paths(fixtures: Path, target_id: str) -> dict[str, Path]:
    return {
        "prep": fixtures / f"{target_id}_prep.pdb",
        "pocket10": fixtures / f"{target_id}_pocket10.pdb",
        "lig": fixtures / f"{target_id}_lig.sdf",
    }


def validate_target_paths(paths: dict[str, Path]) -> None:
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing fixture files: {', '.join(sorted(missing))}")


def reference_box(positions: Any, buffer_angstrom: float) -> tuple[list[float], list[float]]:
    """Return the MolGenBench reference-ligand center and box size."""
    lower = positions.min(axis=0)
    upper = positions.max(axis=0)
    center = ((upper + lower) / 2).tolist()
    size = ((upper - lower) + buffer_angstrom).tolist()
    return center, size


def summarize_runs(runs: list[dict[str, Any]], contract: GateContract) -> dict[str, Any]:
    successful = [run for run in runs if run["status"] == "ok"]
    affinities = [float(run["affinity"]) for run in successful]
    by_seed: dict[int, list[float]] = {}
    for run in successful:
        by_seed.setdefault(int(run["seed"]), []).append(float(run["affinity"]))

    repeat_deltas = {
        str(seed): max(values) - min(values)
        for seed, values in sorted(by_seed.items())
        if len(values) >= 2
    }
    repeatability_complete = bool(by_seed) and all(
        len(values) >= DEFAULT_REPEATS for values in by_seed.values()
    )
    cross_seed_range = max(affinities) - min(affinities) if affinities else None
    median_affinity = median(affinities) if affinities else None
    checks = {
        "all_calls_succeeded": len(successful) == len(runs),
        "repeatability_complete": repeatability_complete,
        "repeat_delta_within_gate": repeatability_complete
        and all(delta <= contract.max_repeat_delta for delta in repeat_deltas.values()),
        "cross_seed_range_within_gate": cross_seed_range is not None
        and cross_seed_range <= contract.max_cross_seed_range,
        "reference_affinity_within_gate": median_affinity is not None
        and median_affinity <= contract.max_reference_affinity,
    }
    return {
        "checks": checks,
        "qualification": "pass" if all(checks.values()) else "fail",
        "median_reference_affinity": median_affinity,
        "cross_seed_affinity_range": cross_seed_range,
        "repeat_affinity_delta_by_seed": repeat_deltas,
    }


def prepare_receptor(source: Path, workdir: Path, python: str) -> Path:
    import AutoDockTools

    receptor = workdir / source.name
    shutil.copy2(source, receptor)
    pqr = receptor.with_suffix(".pqr")
    pdbqt = receptor.with_suffix(".pdbqt")
    subprocess.run(
        ["pdb2pqr30", "--ff=AMBER", str(receptor), str(pqr)],
        check=True,
        capture_output=True,
        text=True,
    )
    prepare_script = (
        Path(AutoDockTools.__path__[0]) / "Utilities24" / "prepare_receptor4.py"
    )
    subprocess.run(
        [python, str(prepare_script), "-r", str(pqr), "-o", str(pdbqt)],
        check=True,
        capture_output=True,
        text=True,
    )
    if not pdbqt.is_file() or pdbqt.stat().st_size == 0:
        raise RuntimeError("receptor preparation produced no PDBQT file")
    return pdbqt


def prepare_ligand(source: Path, output: Path) -> Any:
    from meeko import MoleculePreparation
    from openbabel import pybel
    from rdkit import Chem

    reference = Chem.SDMolSupplier(str(source), removeHs=False)[0]
    if reference is None or reference.GetNumConformers() != 1:
        raise ValueError("reference ligand must contain one readable 3D conformer")
    ob_mol = next(pybel.readfile("sdf", str(source)))
    ob_mol.OBMol.AddHydrogens(False, True, 7.0)
    preparator = MoleculePreparation()
    preparator.prepare(ob_mol.OBMol)
    preparator.write_pdbqt_file(str(output))
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("ligand preparation produced no PDBQT file")
    return reference


def dock_once(
    receptor_pdbqt: Path,
    ligand_pdbqt: Path,
    center: list[float],
    size: list[float],
    seed: int,
    exhaustiveness: int,
) -> float:
    from vina import Vina

    vina = Vina(sf_name="vina", seed=seed, verbosity=0, cpu=exhaustiveness)
    vina.set_receptor(str(receptor_pdbqt))
    vina.set_ligand_from_file(str(ligand_pdbqt))
    vina.compute_vina_maps(center=center, box_size=size)
    vina.dock(exhaustiveness=exhaustiveness, n_poses=1)
    return float(vina.energies(n_poses=1)[0][0])


def qualify_target(
    fixtures: Path,
    target_id: str,
    seeds: tuple[int, ...],
    repeats: int,
    exhaustiveness: int,
    buffer_angstrom: float,
    contract: GateContract,
) -> dict[str, Any]:
    paths = target_paths(fixtures, target_id)
    validate_target_paths(paths)
    started = time.monotonic()
    result: dict[str, Any] = {
        "target_id": target_id,
        "fixture_sha256": {name: sha256_file(path) for name, path in paths.items()},
        "receptor_source": None,
        "runs": [],
    }
    with tempfile.TemporaryDirectory(prefix=f"oracle-{target_id}-") as temp:
        workdir = Path(temp)
        receptor_error: dict[str, str] = {}
        receptor_pdbqt = None
        for source_name in ("prep", "pocket10"):
            try:
                receptor_pdbqt = prepare_receptor(paths[source_name], workdir, sys.executable)
                result["receptor_source"] = source_name
                break
            except Exception as error:  # infrastructure evidence is serialized below
                receptor_error[source_name] = f"{type(error).__name__}: {error}"
        result["receptor_preparation_errors"] = receptor_error
        if receptor_pdbqt is None:
            result["qualification"] = "fail"
            result["failure_stage"] = "receptor_preparation"
            result["elapsed_seconds"] = round(time.monotonic() - started, 6)
            return result

        ligand_pdbqt = workdir / f"{target_id}_lig.pdbqt"
        try:
            reference = prepare_ligand(paths["lig"], ligand_pdbqt)
            positions = reference.GetConformer(0).GetPositions()
            center, size = reference_box(positions, buffer_angstrom)
            result["box_center_angstrom"] = center
            result["box_size_angstrom"] = size
        except Exception as error:
            result["qualification"] = "fail"
            result["failure_stage"] = "ligand_preparation"
            result["error"] = f"{type(error).__name__}: {error}"
            result["elapsed_seconds"] = round(time.monotonic() - started, 6)
            return result

        for seed in seeds:
            for repeat in range(repeats):
                call_started = time.monotonic()
                run = {"seed": seed, "repeat": repeat}
                try:
                    run["affinity"] = dock_once(
                        receptor_pdbqt,
                        ligand_pdbqt,
                        center,
                        size,
                        seed,
                        exhaustiveness,
                    )
                    run["status"] = "ok"
                except Exception as error:
                    run["status"] = "infrastructure_failure"
                    run["error"] = f"{type(error).__name__}: {error}"
                run["elapsed_seconds"] = round(time.monotonic() - call_started, 6)
                result["runs"].append(run)

    result.update(summarize_runs(result["runs"], contract))
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    return result


def package_versions() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version

    packages = [
        "AutoDockTools-py3",
        "meeko",
        "numpy",
        "openbabel",
        "pdb2pqr",
        "rdkit",
        "scipy",
        "vina",
    ]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-found"
    return versions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--targets", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--exhaustiveness", type=int, default=DEFAULT_EXHAUSTIVENESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = GateContract()
    started = time.monotonic()
    report = {
        "schema_version": "1.0",
        "study": "prospective-reaction-environment-selection",
        "scope": "frozen target-panel reference-ligand docking qualification",
        "contract": {
            "seeds": args.seeds,
            "repeats_per_seed": args.repeats,
            "exhaustiveness": args.exhaustiveness,
            "box_buffer_angstrom": DEFAULT_BUFFER_ANGSTROM,
            "max_repeat_affinity_delta": contract.max_repeat_delta,
            "max_cross_seed_affinity_range": contract.max_cross_seed_range,
            "max_reference_affinity": contract.max_reference_affinity,
            "receptor_order": ["full prepared receptor", "10A pocket fallback"],
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": package_versions(),
        },
        "sealed_boundary": {
            "training_or_evaluation_outcomes_read": False,
            "published_model_results_read": False,
            "reference_ligands_used_only_as_oracle_controls": True,
        },
        "targets": [],
    }
    for target_id in args.targets:
        report["targets"].append(
            qualify_target(
                args.fixtures,
                target_id,
                tuple(args.seeds),
                args.repeats,
                args.exhaustiveness,
                DEFAULT_BUFFER_ANGSTROM,
                contract,
            )
        )
    report["qualification"] = (
        "pass"
        if report["targets"] and all(item["qualification"] == "pass" for item in report["targets"])
        else "fail"
    )
    report["elapsed_seconds"] = round(time.monotonic() - started, 6)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["qualification"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
