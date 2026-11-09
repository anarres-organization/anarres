#!/usr/bin/env python3
"""Audit the pinned OMat24 construction reservoir and Alexandria target."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import tarfile
from collections import Counter
from pathlib import Path

import numpy as np

OMAT_ARCHIVE_BYTES = 2_274_568_000
OMAT_ARCHIVE_SHA256 = "789ecc1306575a1652806b339265d7659c57282eeb1b3e3b54ba0e1154938b81"
OMAT_SPLIT_COUNTS = {"train": 1_009_850, "val": 107_732, "test": 53_727}
OMAT_SUBDATASETS = {
    "rattled-1000",
    "rattled-1000-subsampled",
    "rattled-500",
    "rattled-500-subsampled",
    "rattled-300",
    "rattled-300-subsampled",
    "rattled-relax",
    "aimd-from-PBE-1000-npt",
    "aimd-from-PBE-1000-nvt",
    "aimd-from-PBE-3000-npt",
    "aimd-from-PBE-3000-nvt",
}
PBE_CSV_BYTES = 1_451_555
PBE_CSV_SHA256 = "5875695dc44166cf4f09888485c4cfebee03494f65b3e1b3b4b4381620e5d752"
ALEXANDRIA_ARCHIVE_BYTES = 621_251_841
ALEXANDRIA_ARCHIVE_SHA256 = "bdc9f8e93c3d2d11e3c73fcf2c0dd4b0050adae863204c7276eec2e6e0bf6db3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_omat(archive: Path, extracted_root: Path) -> dict:
    assert archive.stat().st_size == OMAT_ARCHIVE_BYTES
    assert sha256(archive) == OMAT_ARCHIVE_SHA256
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
    file_members = [member for member in members if member.isfile()]
    observed_layout: dict[str, set[str]] = {split: set() for split in OMAT_SPLIT_COUNTS}
    for member in file_members:
        parts = member.name.removeprefix("./").split("/")
        if len(parts) >= 3 and parts[0] in observed_layout:
            observed_layout[parts[0]].add(parts[1])
    assert len(members) == 103
    assert all(names == OMAT_SUBDATASETS for names in observed_layout.values())

    counts: dict[str, dict[str, int]] = {}
    atom_counts: dict[str, dict[str, int]] = {}
    for split, expected_total in OMAT_SPLIT_COUNTS.items():
        counts[split] = {}
        atom_counts[split] = {}
        for name in sorted(OMAT_SUBDATASETS):
            metadata = extracted_root / split / name / "metadata.npz"
            database = extracted_root / split / name / f"{split}.aselmdb"
            assert metadata.is_file() and database.is_file()
            with np.load(metadata, allow_pickle=False) as payload:
                natoms = payload["natoms"]
            counts[split][name] = int(len(natoms))
            atom_counts[split][name] = int(natoms.sum())
        assert sum(counts[split].values()) == expected_total
    return {
        "archive": {
            "url": "https://dl.fbaipublicfiles.com/opencatalystproject/data/omat/251210/omat24_1M_251210.tar.gz",
            "bytes": archive.stat().st_size,
            "sha256": OMAT_ARCHIVE_SHA256,
            "members": len(members),
            "unpacked_bytes": sum(member.size for member in members),
        },
        "license": "CC BY 4.0",
        "format": "ASE-compatible LMDB plus natoms metadata",
        "split_record_counts": {split: sum(values.values()) for split, values in counts.items()},
        "split_atom_counts": {split: sum(values.values()) for split, values in atom_counts.items()},
        "subdataset_record_counts": counts,
        "subdataset_atom_counts": atom_counts,
    }


def first_header(handle: tarfile.TarFile, member: tarfile.TarInfo) -> dict:
    stream = handle.extractfile(member)
    assert stream is not None
    atom_count = int(stream.readline().decode("utf-8").strip())
    comment = stream.readline().decode("utf-8").strip()
    required = {
        "lattice": 'Lattice="' in comment,
        "species_positions_forces": "Properties=species:S:1:pos:R:3:forces:R:3" in comment,
        "energy": " energy=" in f" {comment}",
        "stress": " stress=" in f" {comment}",
        "periodic": 'pbc="T T T"' in comment,
    }
    assert all(required.values())
    return {"atom_count": atom_count, "required_fields": required}


def audit_alexandria(source_dir: Path) -> dict:
    csv_path = source_dir / "pbe.csv"
    archive = source_dir / "disp_extxyz.tar.gz"
    assert csv_path.stat().st_size == PBE_CSV_BYTES
    assert archive.stat().st_size == ALEXANDRIA_ARCHIVE_BYTES
    assert sha256(csv_path) == PBE_CSV_SHA256
    assert sha256(archive) == ALEXANDRIA_ARCHIVE_SHA256

    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 9_958
    ids = {row["mp_id"] for row in rows}
    assert len(ids) == len(rows)
    stability = Counter(row["stable"] for row in rows)
    assert stability == {"True": 8_189, "False": 1_769}

    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        files = [
            member for member in members if member.isfile() and member.name.endswith(".extxyz")
        ]
        material_counts = Counter(member.name.split("/")[1] for member in files)
        assert set(material_counts) == ids
        sample = first_header(handle, files[0])
    displacement_counts = sorted(material_counts.values())
    return {
        "metadata": {
            "url": "https://alexandria.icams.rub.de/data/phonon_benchmark/pbe.csv",
            "bytes": csv_path.stat().st_size,
            "sha256": PBE_CSV_SHA256,
            "records": len(rows),
            "stable": stability["True"],
            "unstable": stability["False"],
        },
        "displacements": {
            "url": "https://alexandria.icams.rub.de/data/phonon_benchmark/disp_extxyz.tar.gz",
            "bytes": archive.stat().st_size,
            "sha256": ALEXANDRIA_ARCHIVE_SHA256,
            "archive_members": len(members),
            "extxyz_files": len(files),
            "material_directories": len(material_counts),
            "unpacked_bytes": sum(member.size for member in members),
            "files_per_material": {
                "minimum": min(displacement_counts),
                "median": statistics.median(displacement_counts),
                "maximum": max(displacement_counts),
            },
            "sample_schema": sample,
        },
        "license": "CC BY 4.0",
        "paper": "https://doi.org/10.1038/s41524-025-01650-1",
    }


def audit(alexandria_dir: Path, omat_archive: Path, omat_root: Path) -> dict:
    return {
        "artifact": "anarres_mlip_phonon_source_qualification_v1",
        "status": "qualified",
        "construction_reservoir": audit_omat(omat_archive, omat_root),
        "physical_target": audit_alexandria(alexandria_dir),
        "interpretation_boundary": [
            (
                "The two releases use PBE labels, but pseudopotential, Hubbard-correction, "
                "energy-reference, and stress-convention compatibility require record-level "
                "checks before training."
            ),
            (
                "The OMat24 1M train split is the only construction reservoir; its validation "
                "and test splits remain available for training diagnostics."
            ),
            "Alexandria material identities and displacement labels remain evaluation-only.",
            (
                "Starting-model pretraining exposure is distinct from overlap introduced by the "
                "new post-training experiment and will be reported separately."
            ),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alexandria-dir", type=Path, required=True)
    parser.add_argument("--omat-archive", type=Path, required=True)
    parser.add_argument("--omat-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.alexandria_dir, args.omat_archive, args.omat_root)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "omat_train_records": result["construction_reservoir"]["split_record_counts"][
                    "train"
                ],
                "alexandria_materials": result["physical_target"]["metadata"]["records"],
                "alexandria_displacements": result["physical_target"]["displacements"][
                    "extxyz_files"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
