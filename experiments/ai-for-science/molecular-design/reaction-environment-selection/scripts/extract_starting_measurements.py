#!/usr/bin/env python3
"""Join frozen RxnFlow samples with target scores and graph measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def record_id(
    view_seed: int,
    returned_index: int,
    canonical_smiles: str,
    trajectory: list[dict[str, Any]],
) -> str:
    payload = "|".join(
        (
            "molecular-measurement-v1",
            str(view_seed),
            str(returned_index),
            canonical_smiles,
            canonical_json(trajectory),
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def merge_overlapping_sets(groups: Iterable[set[int]]) -> list[set[int]]:
    merged: list[set[int]] = []
    for group in groups:
        current = set(group)
        overlaps = [existing for existing in merged if current & existing]
        for existing in overlaps:
            current.update(existing)
            merged.remove(existing)
        merged.append(current)
    return sorted(merged, key=lambda item: (min(item), len(item)))


def chemistry_features(smiles: str) -> dict[str, Any]:
    from rdkit import Chem
    from rdkit.Chem.Scaffolds import MurckoScaffold

    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"invalid returned SMILES: {smiles}")
    canonical = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule, includeChirality=False)
    ring_groups = merge_overlapping_sets(set(ring) for ring in molecule.GetRingInfo().AtomRings())
    ring_systems = [
        Chem.MolFragmentToSmiles(
            molecule,
            atomsToUse=sorted(group),
            canonical=True,
            isomericSmiles=False,
        )
        for group in ring_groups
    ]
    heavy_atoms = molecule.GetNumHeavyAtoms()
    degrees = [atom.GetDegree() for atom in molecule.GetAtoms()]
    return {
        "canonical_smiles": canonical,
        "bemis_murcko_scaffold": scaffold or "<acyclic>",
        "ring_systems": sorted(ring_systems),
        "heavy_atoms": heavy_atoms,
        "bonds": molecule.GetNumBonds(),
        "rings": molecule.GetRingInfo().NumRings(),
        "hetero_atoms": sum(atom.GetAtomicNum() not in (1, 6) for atom in molecule.GetAtoms()),
        "mean_atom_degree": float(np.mean(degrees)) if degrees else 0.0,
        "maximum_atom_degree": max(degrees, default=0),
    }


def route_features(trajectory: list[dict[str, Any]]) -> dict[str, Any]:
    reactions = [str(step["reaction"]) for step in trajectory if step.get("reaction") is not None]
    return {
        "generated_action_count": len(trajectory),
        "reaction_depth": len(reactions),
        "reaction_sequence": reactions,
        "reaction_families": sorted(set(reactions)),
        "route_signature": ">".join(reactions) if reactions else "<no-reaction>",
        "building_block_ids": [
            str(block["id"]) for step in trajectory for block in step.get("building_blocks", [])
        ],
    }


def encode_smiles(
    smiles: list[str],
    checkpoint: Path,
    env_dir: Path,
    device: str,
    batch_size: int,
) -> np.ndarray:
    import torch
    from rxnflow.core.types import State
    from rxnflow.envs.graph import GraphBatch, molecule_to_graph_data
    from rxnflow.sampler import RxnFlowSampler

    sampler = RxnFlowSampler(checkpoint, device=device, env_dir=env_dir)
    output = []
    with torch.inference_mode():
        for start in range(0, len(smiles), batch_size):
            states = [State.from_smiles(value) for value in smiles[start : start + batch_size]]
            batch = GraphBatch.from_list(
                [molecule_to_graph_data(state.molecule) for state in states]
            ).to(sampler.device)
            output.append(sampler.model.encode_state(batch).cpu().numpy())
    return np.concatenate(output, axis=0)


def build_records(
    samples: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    embeddings: np.ndarray,
    view_seed: int,
) -> list[dict[str, Any]]:
    if len(samples) != len(scores) or len(samples) != len(embeddings):
        raise ValueError("samples, target scores, and embeddings must have equal length")
    records = []
    for index, (sample, score, embedding) in enumerate(
        zip(samples, scores, embeddings, strict=True)
    ):
        chemistry = chemistry_features(str(sample["smiles"]))
        trajectory = list(sample["traj"])
        route = route_features(trajectory)
        records.append(
            {
                "record_id": record_id(
                    view_seed,
                    index,
                    chemistry["canonical_smiles"],
                    trajectory,
                ),
                "view_seed": view_seed,
                "returned_index": index,
                "smiles": str(sample["smiles"]),
                **chemistry,
                **route,
                "reward_status": score.get("status"),
                "target_reward": score.get("reward"),
                "docking_affinity": score.get("affinity"),
                "qed": score.get("qed"),
                "oracle_elapsed_seconds": score.get("oracle_elapsed_seconds"),
                "graph_embedding": [float(value) for value in embedding],
            }
        )
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(canonical_json(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--view-seed", type=int, required=True)
    parser.add_argument("--attempts", type=int, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    samples = read_jsonl(args.samples)
    scores = read_jsonl(args.scores)
    embeddings = encode_smiles(
        [str(row["smiles"]) for row in samples],
        args.checkpoint,
        args.env_dir,
        args.device,
        args.batch_size,
    )
    records = build_records(samples, scores, embeddings, args.view_seed)
    write_jsonl(args.output, records)
    manifest = {
        "schema_version": "1.0",
        "view_seed": args.view_seed,
        "attempts": args.attempts,
        "returned_records": len(records),
        "embedding_dimension": int(embeddings.shape[1]),
        "samples_sha256": file_sha256(args.samples),
        "scores_sha256": file_sha256(args.scores),
        "checkpoint_sha256": file_sha256(args.checkpoint),
        "output_sha256": file_sha256(args.output),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
