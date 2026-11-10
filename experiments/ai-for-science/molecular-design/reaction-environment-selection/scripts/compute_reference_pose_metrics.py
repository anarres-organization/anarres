#!/usr/bin/env python3
"""Compute Q07820 reference pose metrics with the MolGenBench contract."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed
from posebusters import PoseBusters
from posecheck import PoseCheck
from posecheck.utils.chem import remove_radicals
from posecheck.utils.clashes import count_clashes
from rdkit import Chem
from rdkit.Chem import Lipinski


def valid_molecule(molecule: Chem.Mol | None) -> bool:
    return molecule is not None and "." not in Chem.MolToSmiles(molecule)


def strain_energy(molecule: Chem.Mol | None) -> float | None:
    if not valid_molecule(molecule):
        return None
    try:
        checker = PoseCheck()
        checker.load_ligands_from_mols([molecule])
        return float(checker.calculate_strain_energy()[0])
    except Exception:
        return None


def clash_score(molecule: Chem.Mol | None, protein: Chem.Mol) -> int | None:
    if not valid_molecule(molecule):
        return None
    if Lipinski.NumRotatableBonds(molecule) >= 15:
        return None
    if molecule.GetNumAtoms() == 0:
        return None
    if np.isnan(molecule.GetConformer().GetPositions()).any():
        return None
    try:
        molecule = remove_radicals(Chem.AddHs(molecule, addCoords=True))
        return int(count_clashes(protein, molecule))
    except Exception:
        return None


def posebusters_checks(molecule: Chem.Mol | None, protein_path: Path) -> dict[str, bool]:
    if not valid_molecule(molecule):
        return {}
    try:
        values = (
            PoseBusters(config="dock")
            .bust(mol_pred=molecule, mol_true=None, mol_cond=str(protein_path))
            .droplevel("file")
            .iloc[0]
            .to_dict()
        )
        return {
            str(key): bool(value is True or value == True)  # noqa: E712
            for key, value in values.items()
        }
    except Exception:
        return {}


def score_reference(
    index: int,
    molecule: Chem.Mol | None,
    protein_path: Path,
    clash_protein: Chem.Mol,
) -> dict[str, object]:
    if molecule is None:
        return {
            "index": index,
            "smiles": "",
            "StrainEnergy": "",
            "ClashScore": "",
            "PoseBusterAllValid": False,
            "PoseBusterChecks": "{}",
        }
    checks = posebusters_checks(molecule, protein_path)
    strain = strain_energy(molecule)
    clashes = clash_score(molecule, clash_protein)
    return {
        "index": index,
        "smiles": Chem.MolToSmiles(molecule),
        "StrainEnergy": "" if strain is None else strain,
        "ClashScore": "" if clashes is None else clashes,
        "PoseBusterAllValid": bool(checks) and all(checks.values()),
        "PoseBusterChecks": json.dumps(checks, sort_keys=True),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdf", type=Path, required=True)
    parser.add_argument("--protein", type=Path, required=True)
    parser.add_argument("--pocket", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    molecules = list(Chem.SDMolSupplier(str(args.sdf), removeHs=False))
    if args.limit is not None:
        molecules = molecules[: args.limit]

    # MolGenBench's clash preprocessor loads the protein once per target. This
    # also avoids races in PoseCheck 57a1938, which uses a target-local scratch
    # file while Reduce adds hydrogens.
    pocket_loader = PoseCheck()
    pocket_loader.load_protein_from_pdb(str(args.pocket))
    clash_protein = pocket_loader.protein
    rows = Parallel(n_jobs=args.jobs, verbose=10)(
        delayed(score_reference)(index, molecule, args.protein, clash_protein)
        for index, molecule in enumerate(molecules)
    )
    if not rows:
        raise ValueError("reference SDF contains no records")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
