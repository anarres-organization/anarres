#!/usr/bin/env python3
"""Dock a fixed RxnFlow sample while preserving poses and failure semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from qualify_docking_oracle import sha256_file
from target_reward_adapter import (
    LigandConformerFailure,
    OracleInfrastructureError,
    prepare_generated_ligand,
    unsupported_autodock_atom_type,
)


def canonical_smiles(smiles: str) -> str | None:
    from rdkit import Chem

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or molecule.GetNumAtoms() == 0 or "." in smiles:
        return None
    return Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)


def molecule_key(smiles: str) -> str:
    return hashlib.sha256(smiles.encode()).hexdigest()


def pdbqt_pose_to_molecule(pose: str) -> Any:
    from openbabel import openbabel as ob
    from rdkit import Chem

    conversion = ob.OBConversion()
    if not conversion.SetInAndOutFormats("pdbqt", "pdb"):
        raise OracleInfrastructureError("Open Babel cannot convert PDBQT to PDB")
    molecule = ob.OBMol()
    if not conversion.ReadString(molecule, pose):
        raise OracleInfrastructureError("Open Babel cannot read the docked PDBQT pose")
    converted = Chem.MolFromPDBBlock(conversion.WriteString(molecule), removeHs=False)
    if converted is None or converted.GetNumConformers() != 1:
        raise OracleInfrastructureError("docked pose conversion produced no 3D molecule")
    return converted


def dock_one(
    prepared_target: Path,
    smiles: str,
    output_sdf: Path,
    seed: int,
    exhaustiveness: int,
) -> dict[str, Any]:
    from rdkit import Chem
    from vina import Vina

    manifest = json.loads((prepared_target / "target_manifest.json").read_text())
    receptor = prepared_target / manifest["receptor_pdbqt"]
    if sha256_file(receptor) != manifest["fixture_sha256"]["prepared_receptor"]:
        raise OracleInfrastructureError("prepared receptor hash mismatch")

    with tempfile.TemporaryDirectory(prefix="molecular-endpoint-dock-") as temp:
        ligand_pdbqt = Path(temp) / "ligand.pdbqt"
        try:
            prepare_generated_ligand(smiles, ligand_pdbqt, seed)
        except LigandConformerFailure:
            return {
                "status": "scientific_zero",
                "reason": "ligand_conformer_failure",
            }

        vina = Vina(sf_name="vina", seed=seed, verbosity=0, cpu=exhaustiveness)
        vina.set_receptor(str(receptor))
        try:
            vina.set_ligand_from_file(str(ligand_pdbqt))
        except TypeError as error:
            atom_type = unsupported_autodock_atom_type(error)
            if atom_type is None:
                raise
            return {
                "status": "scientific_zero",
                "reason": "oracle_unsupported_atom_type",
                "atom_type": atom_type,
            }
        vina.compute_vina_maps(
            center=manifest["box_center_angstrom"],
            box_size=manifest["box_size_angstrom"],
        )
        vina.dock(exhaustiveness=exhaustiveness, n_poses=1)
        affinity = float(vina.energies(n_poses=1)[0][0])
        if not math.isfinite(affinity):
            raise OracleInfrastructureError("Vina returned a non-finite affinity")
        pose = pdbqt_pose_to_molecule(vina.poses(n_poses=1))
        pose.SetProp("_Name", molecule_key(smiles))
        pose.SetProp("canonical_smiles", smiles)
        pose.SetDoubleProp("vina_dock", affinity)
        output_sdf.parent.mkdir(parents=True, exist_ok=True)
        temporary = output_sdf.with_name(f"{output_sdf.stem}.tmp.sdf")
        with Chem.SDWriter(str(temporary)) as writer:
            writer.write(pose)
        temporary.replace(output_sdf)
    return {
        "status": "ok",
        "affinity": affinity,
        "pose_sha256": sha256_file(output_sdf),
    }


def run_subprocess(
    script: Path,
    prepared_target: Path,
    smiles: str,
    output_sdf: Path,
    output_json: Path,
    seed: int,
    exhaustiveness: int,
    timeout_seconds: float,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(script),
        "worker",
        "--prepared-target",
        str(prepared_target),
        "--smiles",
        smiles,
        "--output-sdf",
        str(output_sdf),
        "--output-json",
        str(output_json),
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
    except subprocess.TimeoutExpired:
        return {"status": "infrastructure_failure", "reason": "timeout"}
    if completed.returncode != 0 or not output_json.is_file():
        return {
            "status": "infrastructure_failure",
            "reason": "worker_failure",
            "detail": (completed.stderr or completed.stdout).strip()[-2000:],
        }
    try:
        return json.loads(output_json.read_text())
    except json.JSONDecodeError:
        return {"status": "infrastructure_failure", "reason": "invalid_worker_json"}


def expand_attempt_records(
    samples: list[dict[str, Any]],
    attempts: int,
    seed: int,
    unique_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index in range(attempts):
        attempt_id = f"seed{seed}-{index:06d}"
        if index >= len(samples):
            records.append(
                {
                    "attempt_id": attempt_id,
                    "canonical_smiles": "",
                    "infrastructure_status": "ok",
                    "docking_status": "scientific_zero",
                    "reason": "invalid_generated_trajectory",
                    "vina_affinity": None,
                    "pose_sdf": None,
                }
            )
            continue
        canonical = canonical_smiles(str(samples[index].get("smiles", "")))
        if canonical is None:
            records.append(
                {
                    "attempt_id": attempt_id,
                    "canonical_smiles": "",
                    "infrastructure_status": "ok",
                    "docking_status": "scientific_zero",
                    "reason": "invalid_generated_molecule",
                    "vina_affinity": None,
                    "pose_sdf": None,
                }
            )
            continue
        result = unique_results[canonical]
        infrastructure_status = "ok" if result["status"] != "infrastructure_failure" else "failure"
        records.append(
            {
                "attempt_id": attempt_id,
                "canonical_smiles": canonical,
                "infrastructure_status": infrastructure_status,
                "docking_status": result["status"],
                "reason": result.get("reason"),
                "vina_affinity": result.get("affinity"),
                "pose_sdf": result.get("pose_sdf"),
            }
        )
    return records


def read_samples(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def run_panel(args: argparse.Namespace) -> int:
    samples = read_samples(args.samples)
    if len(samples) > args.attempts:
        raise ValueError("returned samples exceed the frozen attempt count")
    canonical = [canonical_smiles(str(item.get("smiles", ""))) for item in samples]
    unique = sorted({item for item in canonical if item is not None})
    pose_dir = args.output_dir / "poses"
    result_dir = args.output_dir / "unique-results"
    pose_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, Any]] = {}
    script = Path(__file__).resolve()

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {}
        for smiles in unique:
            key = molecule_key(smiles)
            pose = pose_dir / f"{key}.sdf"
            output = result_dir / f"{key}.json"
            if output.is_file():
                result = json.loads(output.read_text())
                if result.get("status") == "ok" and not pose.is_file():
                    raise ValueError(f"completed record lacks pose: {key}")
                result["pose_sdf"] = str(pose) if pose.is_file() else None
                results[smiles] = result
                continue
            future = executor.submit(
                run_subprocess,
                script,
                args.prepared_target,
                smiles,
                pose,
                output,
                args.seed,
                args.exhaustiveness,
                args.timeout_seconds,
            )
            futures[future] = (smiles, pose)
        for future in as_completed(futures):
            smiles, pose = futures[future]
            result = future.result()
            result["pose_sdf"] = str(pose) if pose.is_file() else None
            results[smiles] = result

    attempts = expand_attempt_records(samples, args.attempts, args.sample_seed, results)
    write_jsonl(args.output_records, attempts)
    infrastructure_failures = sum(item["infrastructure_status"] != "ok" for item in attempts)
    report = {
        "schema_version": "1.0",
        "contract": "q07820-starting-policy-endpoint-qualification-v1",
        "status": "complete" if infrastructure_failures == 0 else "invalid",
        "sample_seed": args.sample_seed,
        "attempts": args.attempts,
        "returned_samples": len(samples),
        "unique_valid_molecules": len(unique),
        "unique_docking_status": {
            status: sum(result["status"] == status for result in results.values())
            for status in ("ok", "scientific_zero", "infrastructure_failure")
        },
        "infrastructure_failures": infrastructure_failures,
        "inputs": {
            "samples_sha256": sha256_file(args.samples),
            "prepared_target_manifest_sha256": sha256_file(
                args.prepared_target / "target_manifest.json"
            ),
        },
        "output_records_sha256": sha256_file(args.output_records),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if infrastructure_failures == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    worker = subparsers.add_parser("worker")
    worker.add_argument("--prepared-target", type=Path, required=True)
    worker.add_argument("--smiles", required=True)
    worker.add_argument("--output-sdf", type=Path, required=True)
    worker.add_argument("--output-json", type=Path, required=True)
    worker.add_argument("--seed", type=int, required=True)
    worker.add_argument("--exhaustiveness", type=int, required=True)

    panel = subparsers.add_parser("panel")
    panel.add_argument("--samples", type=Path, required=True)
    panel.add_argument("--prepared-target", type=Path, required=True)
    panel.add_argument("--attempts", type=int, required=True)
    panel.add_argument("--sample-seed", type=int, required=True)
    panel.add_argument("--seed", type=int, default=20261108)
    panel.add_argument("--exhaustiveness", type=int, default=8)
    panel.add_argument("--timeout-seconds", type=float, default=300.0)
    panel.add_argument("--jobs", type=int, default=8)
    panel.add_argument("--output-dir", type=Path, required=True)
    panel.add_argument("--output-records", type=Path, required=True)
    panel.add_argument("--report", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "worker":
        try:
            result = dock_one(
                args.prepared_target,
                args.smiles,
                args.output_sdf,
                args.seed,
                args.exhaustiveness,
            )
        except Exception as error:
            raise OracleInfrastructureError(
                f"pose-preserving docking failed: {type(error).__name__}: {error}"
            ) from error
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 0
    return run_panel(args)


if __name__ == "__main__":
    raise SystemExit(main())
