#!/usr/bin/env python3
"""Structured RxnFlow target reward backed by the frozen docking oracle."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from qualify_docking_oracle import dock_once, prepare_receptor, reference_box

DEFAULT_SEED = 20261108
DEFAULT_EXHAUSTIVENESS = 8
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_BOX_BUFFER_ANGSTROM = 5.0


class OracleInfrastructureError(RuntimeError):
    """Raised when scientific reward is unavailable because the oracle failed."""


class LigandConformerFailure(ValueError):
    """A valid molecule cannot produce a deterministic docking conformer."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def terminal_reward(affinity: float, qed: float) -> float:
    """Convert lower-is-better Vina affinity and QED into RxnFlow reward."""
    if not math.isfinite(affinity) or not math.isfinite(qed):
        raise ValueError("affinity and QED must be finite")
    if not 0.0 <= qed <= 1.0:
        raise ValueError("QED must lie in [0, 1]")
    return max(-affinity, 0.0) * qed


def molecule_assessment(smiles: str) -> dict[str, Any]:
    """Return scientific eligibility without invoking the docking oracle."""
    from rdkit import Chem
    from rdkit.Chem import QED, Crippen, rdMolDescriptors

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        return {
            "status": "scientific_zero",
            "reason": "invalid_molecule",
            "reward": 0.0,
        }

    metrics = {
        "exact_molecular_weight": float(rdMolDescriptors.CalcExactMolWt(molecule)),
        "hydrogen_bond_donors": int(rdMolDescriptors.CalcNumHBD(molecule)),
        "hydrogen_bond_acceptors": int(rdMolDescriptors.CalcNumHBA(molecule)),
        "logp": float(Crippen.MolLogP(molecule)),
        "tpsa": float(rdMolDescriptors.CalcTPSA(molecule)),
        "rotatable_bonds": int(rdMolDescriptors.CalcNumRotatableBonds(molecule)),
        "qed": float(QED.qed(molecule)),
    }
    violations = []
    if metrics["exact_molecular_weight"] > 500.0:
        violations.append("molecular_weight")
    if metrics["hydrogen_bond_donors"] > 5:
        violations.append("hydrogen_bond_donors")
    if metrics["hydrogen_bond_acceptors"] > 10:
        violations.append("hydrogen_bond_acceptors")
    if metrics["logp"] > 5.0:
        violations.append("logp")
    if metrics["tpsa"] > 140.0:
        violations.append("tpsa")
    if metrics["rotatable_bonds"] > 10:
        violations.append("rotatable_bonds")
    if violations:
        return {
            "status": "scientific_zero",
            "reason": "eligibility_filter",
            "violations": violations,
            "metrics": metrics,
            "reward": 0.0,
        }
    return {"status": "eligible", "metrics": metrics}


def prepare_target(
    prep_pdb: Path,
    pocket_pdb: Path,
    reference_ligand: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Prepare one target once and record the reference-defined docking box."""
    from rdkit import Chem

    output_dir.mkdir(parents=True, exist_ok=True)
    errors: dict[str, str] = {}
    receptor_pdbqt = None
    receptor_source = None
    for name, source in (("prep", prep_pdb), ("pocket10", pocket_pdb)):
        try:
            receptor_pdbqt = prepare_receptor(source, output_dir, sys.executable)
            receptor_source = name
            break
        except Exception as error:
            errors[name] = f"{type(error).__name__}: {error}"
    if receptor_pdbqt is None:
        raise OracleInfrastructureError(
            "receptor preparation failed for full receptor and pocket fallback"
        )

    copied_reference = output_dir / "reference_ligand.sdf"
    shutil.copy2(reference_ligand, copied_reference)
    molecule = Chem.SDMolSupplier(str(copied_reference), removeHs=False)[0]
    if molecule is None or molecule.GetNumConformers() != 1:
        raise OracleInfrastructureError("reference ligand must contain one readable 3D conformer")
    center, size = reference_box(
        molecule.GetConformer(0).GetPositions(), DEFAULT_BOX_BUFFER_ANGSTROM
    )
    manifest = {
        "schema_version": "1.0",
        "receptor_source": receptor_source,
        "receptor_preparation_errors": errors,
        "receptor_pdbqt": receptor_pdbqt.name,
        "reference_ligand": copied_reference.name,
        "box_center_angstrom": center,
        "box_size_angstrom": size,
        "fixture_sha256": {
            "prep": sha256_file(prep_pdb),
            "pocket10": sha256_file(pocket_pdb),
            "reference_ligand": sha256_file(reference_ligand),
            "prepared_receptor": sha256_file(receptor_pdbqt),
        },
    }
    (output_dir / "target_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def prepare_generated_ligand(smiles: str, output: Path, seed: int) -> None:
    """Follow MolGenBench's generated-ligand embedding and Meeko preparation."""
    from meeko import MoleculePreparation
    from openbabel import pybel
    from rdkit import Chem
    from rdkit.Chem import AllChem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError("invalid molecule reached docking worker")
    molecule = Chem.AddHs(molecule)
    parameters = AllChem.ETKDGv3()
    parameters.randomSeed = seed
    if AllChem.EmbedMolecule(molecule, parameters) != 0:
        molecule.RemoveAllConformers()
        parameters = AllChem.ETKDGv3()
        parameters.randomSeed = seed
        parameters.useRandomCoords = True
        if AllChem.EmbedMolecule(molecule, parameters) != 0:
            raise LigandConformerFailure("conformer embedding failed")
    if AllChem.MMFFHasAllMoleculeParams(molecule):
        AllChem.MMFFOptimizeMolecule(molecule)

    sdf_path = output.with_suffix(".sdf")
    with Chem.SDWriter(str(sdf_path)) as writer:
        writer.write(molecule)
    ob_molecule = next(pybel.readfile("sdf", str(sdf_path)))
    preparator = MoleculePreparation()
    with contextlib.redirect_stdout(io.StringIO()):
        preparator.prepare(ob_molecule.OBMol)
        preparator.write_pdbqt_file(str(output))
    if not output.is_file() or output.stat().st_size == 0:
        raise OracleInfrastructureError("ligand preparation produced no PDBQT")


def docking_worker(
    prepared_target: Path,
    smiles: str,
    output: Path,
    seed: int,
    exhaustiveness: int,
) -> None:
    manifest = json.loads((prepared_target / "target_manifest.json").read_text())
    receptor = prepared_target / manifest["receptor_pdbqt"]
    if sha256_file(receptor) != manifest["fixture_sha256"]["prepared_receptor"]:
        raise OracleInfrastructureError("prepared receptor hash mismatch")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="molecular-reward-") as temp:
        ligand_pdbqt = Path(temp) / "ligand.pdbqt"
        try:
            prepare_generated_ligand(smiles, ligand_pdbqt, seed)
        except LigandConformerFailure:
            output.write_text(
                json.dumps(
                    {
                        "status": "scientific_zero",
                        "reason": "ligand_conformer_failure",
                        "reward": 0.0,
                        "elapsed_seconds": round(time.monotonic() - started, 6),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            return
        affinity = dock_once(
            receptor,
            ligand_pdbqt,
            manifest["box_center_angstrom"],
            manifest["box_size_angstrom"],
            seed,
            exhaustiveness,
        )
    result = {
        "status": "ok",
        "affinity": affinity,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


def run_worker(
    prepared_target: Path,
    smiles: str,
    timeout_seconds: float,
    seed: int = DEFAULT_SEED,
    exhaustiveness: int = DEFAULT_EXHAUSTIVENESS,
) -> dict[str, Any]:
    """Run docking in a killable subprocess and reject incomplete evidence."""
    with tempfile.TemporaryDirectory(prefix="molecular-oracle-call-") as temp:
        output = Path(temp) / "worker_result.json"
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "worker",
            "--prepared-target",
            str(prepared_target),
            "--smiles",
            smiles,
            "--output",
            str(output),
            "--seed",
            str(seed),
            "--exhaustiveness",
            str(exhaustiveness),
        ]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise OracleInfrastructureError(
                f"docking exceeded {timeout_seconds:g} seconds"
            ) from error
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise OracleInfrastructureError(
                f"docking worker exited {completed.returncode}: {detail}"
            )
        if not output.is_file():
            raise OracleInfrastructureError("docking worker produced no result")
        try:
            result = json.loads(output.read_text())
        except json.JSONDecodeError as error:
            raise OracleInfrastructureError("docking worker produced invalid JSON") from error
        if result.get("status") == "scientific_zero":
            if result.get("reason") != "ligand_conformer_failure":
                raise OracleInfrastructureError("worker returned an unknown scientific zero")
            return result
        if result.get("status") != "ok" or not math.isfinite(result.get("affinity", math.nan)):
            raise OracleInfrastructureError("docking worker returned invalid affinity")
        return result


def score_smiles(
    prepared_target: Path,
    smiles: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Return a scientific score or raise on unavailable oracle evidence."""
    assessment = molecule_assessment(smiles)
    if assessment["status"] == "scientific_zero":
        return assessment
    oracle = run_worker(prepared_target, smiles, timeout_seconds)
    if oracle["status"] == "scientific_zero":
        return {
            key: value
            for key, value in {
                **oracle,
                "metrics": assessment["metrics"],
                "oracle_elapsed_seconds": oracle["elapsed_seconds"],
            }.items()
            if key != "elapsed_seconds"
        }
    qed = assessment["metrics"]["qed"]
    return {
        "status": "ok",
        "affinity": oracle["affinity"],
        "qed": qed,
        "reward": terminal_reward(oracle["affinity"], qed),
        "metrics": assessment["metrics"],
        "oracle_elapsed_seconds": oracle["elapsed_seconds"],
    }


def score_batch(
    prepared_target: Path,
    smiles_list: list[str],
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_workers: int = 1,
) -> list[dict[str, Any]]:
    """Score a batch concurrently while preserving order and duplicate identity."""
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    assessments = [molecule_assessment(smiles) for smiles in smiles_list]
    unique_eligible = list(
        dict.fromkeys(
            smiles
            for smiles, assessment in zip(smiles_list, assessments, strict=True)
            if assessment["status"] == "eligible"
        )
    )
    oracle_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_worker, prepared_target, smiles, timeout_seconds): smiles
            for smiles in unique_eligible
        }
        try:
            for future in as_completed(futures):
                oracle_results[futures[future]] = future.result()
        except Exception:
            for future in futures:
                future.cancel()
            raise

    results = []
    for smiles, assessment in zip(smiles_list, assessments, strict=True):
        if assessment["status"] == "scientific_zero":
            results.append(assessment)
            continue
        oracle = oracle_results[smiles]
        if oracle["status"] == "scientific_zero":
            results.append(
                {
                    key: value
                    for key, value in {
                        **oracle,
                        "metrics": assessment["metrics"],
                        "oracle_elapsed_seconds": oracle["elapsed_seconds"],
                    }.items()
                    if key != "elapsed_seconds"
                }
            )
            continue
        qed = assessment["metrics"]["qed"]
        results.append(
            {
                "status": "ok",
                "affinity": oracle["affinity"],
                "qed": qed,
                "reward": terminal_reward(oracle["affinity"], qed),
                "metrics": assessment["metrics"],
                "oracle_elapsed_seconds": oracle["elapsed_seconds"],
            }
        )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare-target")
    prepare.add_argument("--prep-pdb", type=Path, required=True)
    prepare.add_argument("--pocket-pdb", type=Path, required=True)
    prepare.add_argument("--reference-ligand", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)

    worker = commands.add_parser("worker")
    worker.add_argument("--prepared-target", type=Path, required=True)
    worker.add_argument("--smiles", required=True)
    worker.add_argument("--output", type=Path, required=True)
    worker.add_argument("--seed", type=int, default=DEFAULT_SEED)
    worker.add_argument("--exhaustiveness", type=int, default=DEFAULT_EXHAUSTIVENESS)

    score = commands.add_parser("score")
    score.add_argument("--prepared-target", type=Path, required=True)
    score.add_argument("--smiles", required=True)
    score.add_argument("--output", type=Path, required=True)
    score.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)

    batch = commands.add_parser("score-batch")
    batch.add_argument("--prepared-target", type=Path, required=True)
    batch.add_argument("--input", type=Path, required=True)
    batch.add_argument("--output", type=Path, required=True)
    batch.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    batch.add_argument("--max-workers", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare-target":
        manifest = prepare_target(
            args.prep_pdb,
            args.pocket_pdb,
            args.reference_ligand,
            args.output_dir,
        )
        print(json.dumps(manifest, sort_keys=True))
        return 0
    if args.command == "worker":
        docking_worker(
            args.prepared_target,
            args.smiles,
            args.output,
            args.seed,
            args.exhaustiveness,
        )
        return 0
    if args.command == "score-batch":
        smiles_list = [
            json.loads(line)["smiles"]
            for line in args.input.read_text().splitlines()
            if line.strip()
        ]
        try:
            results = score_batch(
                args.prepared_target,
                smiles_list,
                args.timeout_seconds,
                args.max_workers,
            )
            return_code = 0
        except OracleInfrastructureError as error:
            results = [
                {
                    "status": "infrastructure_failure",
                    "error": f"{type(error).__name__}: {error}",
                }
            ]
            return_code = 2
        args.output.write_text(
            "".join(json.dumps(result, sort_keys=True) + "\n" for result in results)
        )
        return return_code
    try:
        result = score_smiles(args.prepared_target, args.smiles, args.timeout_seconds)
        return_code = 0
    except OracleInfrastructureError as error:
        result = {
            "status": "infrastructure_failure",
            "error": f"{type(error).__name__}: {error}",
        }
        return_code = 2
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
