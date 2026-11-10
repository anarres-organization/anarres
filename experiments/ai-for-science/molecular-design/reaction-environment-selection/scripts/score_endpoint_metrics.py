#!/usr/bin/env python3
"""Compute the frozen MolGenBench endpoint metrics for a docked panel."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
from collections import Counter
from pathlib import Path
from typing import Any

_PROTEIN_PATH: str | None = None
_CLASH_PROTEIN: Any = None
_METRICS: dict[str, Any] = {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def chemical_filter_pass(value: Any) -> bool:
    """Normalize MolGenBench's scalar Boolean without requiring Python identity."""

    return bool(isinstance(value, dict) and bool(value.get("ChemFilter", False)))


def verify_chemical_filter_runtime(finder: Any = None) -> dict[str, str]:
    """Require the complete pinned Lilly runtime before scoring any molecule."""

    if finder is None:
        from medchem.structural.lilly_demerits._lilly import find_lilly_binaries

        finder = find_lilly_binaries
    binaries = finder()
    expected = {"mc_first_pass", "tsubstructure", "iwdemerit"}
    if set(binaries) != expected:
        raise RuntimeError("the Lilly chemical-filter runtime is incomplete")
    return {name: sha256_file(Path(path)) for name, path in sorted(binaries.items())}


def initialize_pose_workers(protein_path: str, clash_protein: Any) -> None:
    from molgenbench.metrics.basic import ChemFilterMetric, QEDMetric, SAMetric, ValidMetric
    from molgenbench.metrics.conformer import PoseBusterMetric

    global _CLASH_PROTEIN, _METRICS, _PROTEIN_PATH
    _PROTEIN_PATH = protein_path
    _CLASH_PROTEIN = clash_protein
    _METRICS = {
        "valid": ValidMetric(),
        "qed": QEDMetric(),
        "sa": SAMetric(),
        "chem": ChemFilterMetric(),
        "posebusters": PoseBusterMetric(),
    }


def score_unique_pose(task: tuple[str, str]) -> tuple[str, dict[str, Any]]:
    import numpy as np
    from molgenbench.io.types import MoleculeRecord
    from posecheck import PoseCheck
    from posecheck.utils.chem import remove_radicals
    from posecheck.utils.clashes import count_clashes
    from rdkit import Chem
    from rdkit.Chem import Lipinski

    canonical_smiles, pose_path = task
    base_molecule = Chem.MolFromSmiles(canonical_smiles)
    pose_molecule = next(
        (mol for mol in Chem.SDMolSupplier(pose_path, removeHs=False) if mol is not None),
        None,
    )
    if base_molecule is None or pose_molecule is None:
        return canonical_smiles, {
            "valid": False,
            "qed": None,
            "synthetic_accessibility": None,
            "chemical_filters_pass": False,
            "posebusters_all_valid": False,
            "strain_energy": None,
            "clash_score": None,
            "pose_metric_status": "scientific_zero",
            "reason": "invalid_endpoint_molecule",
        }

    base_record = MoleculeRecord(
        id=canonical_smiles,
        smiles=canonical_smiles,
        uniprot="Q07820",
        series=None,
        round="starting-policy",
        rdkit_mol=base_molecule,
        metadata={},
    )
    valid = _METRICS["valid"].compute(base_record) is True
    qed = finite_number(_METRICS["qed"].compute(base_record))
    sa = finite_number(_METRICS["sa"].compute(base_record))
    chem = _METRICS["chem"].compute(base_record)
    chemical_filters_pass = chemical_filter_pass(chem)

    pose_record = MoleculeRecord(
        id=canonical_smiles,
        smiles=canonical_smiles,
        uniprot="Q07820",
        series=None,
        round="starting-policy",
        rdkit_mol=pose_molecule,
        metadata={"protein_path": _PROTEIN_PATH},
    )
    checks = _METRICS["posebusters"].compute(pose_record)
    posebusters_all_valid = bool(checks) and all(bool(value) for value in checks.values())

    try:
        strain_checker = PoseCheck()
        strain_checker.load_ligands_from_mols([pose_molecule])
        strain_energy = finite_number(strain_checker.calculate_strain_energy()[0])
    except Exception:
        strain_energy = None

    clash_score: float | None = None
    if (
        pose_molecule.GetNumAtoms() > 0
        and pose_molecule.GetNumConformers() == 1
        and not np.isnan(pose_molecule.GetConformer().GetPositions()).any()
        and Lipinski.NumRotatableBonds(pose_molecule) < 15
    ):
        try:
            clash_ligand = remove_radicals(Chem.AddHs(pose_molecule, addCoords=True))
            clash_score = finite_number(count_clashes(_CLASH_PROTEIN, clash_ligand))
        except Exception:
            clash_score = None

    return canonical_smiles, {
        "valid": valid,
        "qed": qed,
        "synthetic_accessibility": sa,
        "chemical_filters_pass": chemical_filters_pass,
        "posebusters_all_valid": posebusters_all_valid,
        "strain_energy": strain_energy,
        "clash_score": clash_score,
        "pose_metric_status": "complete",
        "reason": None,
    }


def flatten_interaction_row(row: Any) -> dict[str, bool]:
    return {
        f"{residue}_{interaction}": bool(value) for (_, residue, interaction), value in row.items()
    }


def interaction_ready_records(
    metric: Any,
    records: list[tuple[str, Any]],
) -> list[tuple[str, Any]]:
    """Preserve identities for records retained by MolGenBench preparation."""

    ready: list[tuple[str, Any]] = []
    for smiles, record in records:
        prepared = metric._filter_ligands(metric._prepare_ligands([record]))
        if len(prepared) == 1:
            ready.append((smiles, record))
    return ready


def interaction_reference_map(
    reference_scores_path: Path,
) -> tuple[dict[str, float], dict[str, Any]]:
    import pandas as pd
    from molgenbench.metrics.conformer import InteractionScoreMetric

    metric = InteractionScoreMetric()
    frame = pd.read_csv(reference_scores_path)
    if frame.empty or "InteractionScore" not in frame:
        raise RuntimeError("reference interaction score table is empty or malformed")
    fingerprints = frame.drop(columns=["InteractionScore"])
    reference_map = metric.getInteractionMap(fingerprints)
    if not reference_map or not math.isclose(sum(reference_map.values()), 1.0):
        raise RuntimeError("reference interaction map is empty or unnormalized")
    reproduced = [
        metric.getInteractionScores(row.to_dict(), reference_map)
        for _, row in fingerprints.iterrows()
    ]
    maximum_error = max(
        abs(float(expected) - observed)
        for expected, observed in zip(frame["InteractionScore"], reproduced, strict=True)
    )
    if maximum_error > 1e-12:
        raise RuntimeError("reference interaction scores do not reproduce")
    return reference_map, {
        "rows": len(frame),
        "features": len(reference_map),
        "maximum_absolute_reproduction_error": maximum_error,
    }


def score_interaction_batch(
    work: tuple[list[tuple[str, str]], str, dict[str, float]],
) -> dict[str, float | None]:
    from molgenbench.io.types import MoleculeRecord
    from molgenbench.metrics.conformer import InteractionScoreMetric
    from rdkit import Chem

    batch, protein_path, reference_map = work
    metric = InteractionScoreMetric()
    scores: dict[str, float | None] = {smiles: None for smiles, _ in batch}
    eligible: list[tuple[str, Any]] = []
    for smiles, pose_path in batch:
        molecule = next(
            (mol for mol in Chem.SDMolSupplier(pose_path, removeHs=False) if mol is not None),
            None,
        )
        if molecule is not None and metric._filterMol(molecule):
            eligible.append((smiles, molecule))
    records: list[tuple[str, Any]] = []
    for smiles, molecule in eligible:
        record = MoleculeRecord(
            id=smiles,
            smiles=smiles,
            uniprot="Q07820",
            series=None,
            round="starting-policy",
            rdkit_mol=molecule,
            metadata={"protein_path": protein_path},
        )
        records.append((smiles, record))
    records = interaction_ready_records(metric, records)
    if not records:
        return scores
    frame = metric._compute_fp_df([record for _, record in records], protein_path)
    if len(frame) != len(records):
        raise RuntimeError("candidate interaction rows do not match eligible molecules")
    for (smiles, _), (_, row) in zip(records, frame.iterrows(), strict=True):
        flat = flatten_interaction_row(row)
        scores[smiles] = finite_number(metric.getInteractionScores(flat, reference_map))
    return scores


def compute_interaction_scores(
    tasks: list[tuple[str, str]],
    protein_path: Path,
    reference_map: dict[str, float],
    batch_size: int,
    jobs: int,
) -> dict[str, float | None]:
    scores: dict[str, float | None] = {smiles: None for smiles, _ in tasks}
    batches = [
        (tasks[start : start + batch_size], str(protein_path), reference_map)
        for start in range(0, len(tasks), batch_size)
    ]
    context = multiprocessing.get_context("fork")
    with context.Pool(processes=jobs) as pool:
        for result in pool.imap_unordered(score_interaction_batch, batches):
            scores.update(result)
    return scores


def expand_endpoint_records(
    docking_records: list[dict[str, Any]],
    unique_metrics: dict[str, dict[str, Any]],
    interaction_scores: dict[str, float | None],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for docking in docking_records:
        smiles = str(docking.get("canonical_smiles", ""))
        usable_pose = (
            docking.get("infrastructure_status") == "ok"
            and docking.get("docking_status") == "ok"
            and smiles in unique_metrics
        )
        metrics = unique_metrics.get(smiles, {}) if usable_pose else {}
        rows.append(
            {
                "attempt_id": str(docking["attempt_id"]),
                "canonical_smiles": smiles,
                "infrastructure_status": docking.get("infrastructure_status"),
                "valid": metrics.get("valid", False),
                "vina_affinity": docking.get("vina_affinity"),
                "qed": metrics.get("qed"),
                "synthetic_accessibility": metrics.get("synthetic_accessibility"),
                "chemical_filters_pass": metrics.get("chemical_filters_pass", False),
                "posebusters_all_valid": metrics.get("posebusters_all_valid", False),
                "strain_energy": metrics.get("strain_energy"),
                "clash_score": metrics.get("clash_score"),
                "interaction_score": interaction_scores.get(smiles) if usable_pose else None,
                "docking_status": docking.get("docking_status"),
                "endpoint_status": metrics.get("pose_metric_status", "scientific_zero"),
                "reason": docking.get("reason") or metrics.get("reason"),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docking-records", type=Path, required=True)
    parser.add_argument("--protein", type=Path, required=True)
    parser.add_argument("--pocket", type=Path, required=True)
    parser.add_argument("--reference-actives", type=Path, required=True)
    parser.add_argument("--reference-interaction-scores", type=Path, required=True)
    parser.add_argument("--attempts", type=int, required=True)
    parser.add_argument(
        "--contract",
        default="q07820-starting-policy-endpoint-qualification-v1",
    )
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--interaction-jobs", type=int, default=8)
    parser.add_argument("--interaction-batch-size", type=int, default=128)
    parser.add_argument("--output-records", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    from posecheck import PoseCheck

    args = parse_args()
    docking_records = read_jsonl(args.docking_records)
    if len(docking_records) != args.attempts:
        raise ValueError("docking records do not match the frozen attempt count")
    if any(row.get("infrastructure_status") != "ok" for row in docking_records):
        raise RuntimeError("docking panel contains infrastructure failures")
    chemical_filter_runtime = verify_chemical_filter_runtime()

    unique_pose_paths: dict[str, str] = {}
    for row in docking_records:
        if row.get("docking_status") != "ok":
            continue
        smiles = str(row["canonical_smiles"])
        pose_path = str(row["pose_sdf"])
        if smiles in unique_pose_paths and unique_pose_paths[smiles] != pose_path:
            raise ValueError("one canonical molecule maps to multiple docked poses")
        if not Path(pose_path).is_file():
            raise ValueError(f"docked pose is missing: {pose_path}")
        unique_pose_paths[smiles] = pose_path
    tasks = sorted(unique_pose_paths.items())

    clash_loader = PoseCheck()
    clash_loader.load_protein_from_pdb(str(args.pocket))
    if clash_loader.protein is None:
        raise RuntimeError("pocket preparation produced no clash protein")

    context = multiprocessing.get_context("fork")
    with context.Pool(
        processes=args.jobs,
        initializer=initialize_pose_workers,
        initargs=(str(args.protein), clash_loader.protein),
    ) as pool:
        unique_metrics = dict(pool.imap_unordered(score_unique_pose, tasks, chunksize=4))
    if len(unique_metrics) != len(tasks):
        raise RuntimeError("pose metric results do not cover every docked molecule")

    reference_map, reference_validation = interaction_reference_map(
        args.reference_interaction_scores,
    )
    interaction_scores = compute_interaction_scores(
        tasks,
        args.protein,
        reference_map,
        args.interaction_batch_size,
        args.interaction_jobs,
    )
    rows = expand_endpoint_records(docking_records, unique_metrics, interaction_scores)
    write_jsonl(args.output_records, rows)

    available = {
        field: sum(row[field] is not None for row in rows)
        for field in (
            "vina_affinity",
            "qed",
            "synthetic_accessibility",
            "strain_energy",
            "clash_score",
            "interaction_score",
        )
    }
    report = {
        "schema_version": "1.0",
        "contract": args.contract,
        "status": "complete",
        "attempts": len(rows),
        "unique_docked_molecules": len(tasks),
        "metric_availability_by_attempt": available,
        "docking_status_by_attempt": dict(
            sorted(Counter(row["docking_status"] for row in rows).items())
        ),
        "reference_interaction_validation": reference_validation,
        "chemical_filter_runtime_sha256": chemical_filter_runtime,
        "inputs": {
            "docking_records_sha256": sha256_file(args.docking_records),
            "protein_sha256": sha256_file(args.protein),
            "pocket_sha256": sha256_file(args.pocket),
            "reference_actives_sha256": sha256_file(args.reference_actives),
            "reference_interaction_scores_sha256": sha256_file(args.reference_interaction_scores),
        },
        "output_records_sha256": sha256_file(args.output_records),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
