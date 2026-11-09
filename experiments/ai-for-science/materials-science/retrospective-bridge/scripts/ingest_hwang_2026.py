#!/usr/bin/env python3
"""Build matched surface-training regime panels from Hwang et al. (2026)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_ID = "hwang_2026_surface_finetuning"
DOI = "10.1016/j.commatsci.2026.114666"
REPOSITORY_REVISION = "4a1c96f9badbb1676d83103a0c9e0f4a16e65e28"

SYSTEMS = {
    "Fig_2a.csv": {
        "material_system": "gold_surfaces",
        "formula": "Au",
        "composition_class": "unary",
        "sha256": "2bfc358b7656aa74d83a2c175b71629752fdbd2eaedc0732ec9adb8f5c5349c1",
    },
    "Fig_2c.csv": {
        "material_system": "ruthenium_dioxide_surfaces",
        "formula": "RuO2",
        "composition_class": "binary",
        "sha256": "f0180c663297864dafc126377df44c197b690ed93b74bb5a43d74fbee2d6c5f4",
    },
    "Fig_2e.csv": {
        "material_system": "bismuth_vanadate_surfaces",
        "formula": "BiVO4",
        "composition_class": "ternary",
        "sha256": "9c8e86aa8e4e91e19854c3cc61e8b04d15154f360313a32aead317bdfe5909ca",
    },
}

REPOSITORY_FILES = {
    "README.md": "397c683042dd429328fe5ce7f4fc06713ff7f3f7cc479e6829d8c4acbb72f5ea",
    "LICENSE": "032bf41f31142c6596636dc1ef0734864173b3441b6c3c8c67daa95a0b206c61",
}

ENDPOINTS = {
    "energy_rmse": ("E_meV", "meV_per_atom"),
    "force_rmse": ("F_meV", "meV_per_A"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_revision(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def validate_repository(root: Path) -> None:
    if repository_revision(root) != REPOSITORY_REVISION:
        raise ValueError("unexpected UIP-surface-finetuning repository revision")
    for name, expected in REPOSITORY_FILES.items():
        if sha256(root / name) != expected:
            raise ValueError(f"checksum mismatch for {name}")
    for name, metadata in SYSTEMS.items():
        if sha256(root / "data" / name) != metadata["sha256"]:
            raise ValueError(f"checksum mismatch for data/{name}")


def read_curves(path: Path) -> dict[str, dict[int, dict[str, float]]]:
    curves: dict[str, dict[int, dict[str, float]]] = {
        "fine_tuning": {},
        "training_from_scratch": {},
    }
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        header = next(rows)
        if header != ["N_FT", "E_meV", "F_meV", "N_TS", "E_meV", "F_meV"]:
            raise ValueError(f"unexpected columns in {path.name}")
        for row in rows:
            for environment, offset in (
                ("fine_tuning", 0),
                ("training_from_scratch", 3),
            ):
                budget_text = row[offset].strip()
                if not budget_text:
                    continue
                budget = int(budget_text)
                curves[environment][budget] = {
                    "energy_rmse": float(row[offset + 1]),
                    "force_rmse": float(row[offset + 2]),
                }
    return curves


def ingest(*, repository: Path) -> dict:
    validate_repository(repository)
    decisions = []
    matched_budgets: dict[str, list[int]] = {}
    for filename, system in SYSTEMS.items():
        curves = read_curves(repository / "data" / filename)
        budgets = sorted(set(curves["fine_tuning"]) & set(curves["training_from_scratch"]))
        matched_budgets[system["formula"]] = budgets
        for budget in budgets:
            for endpoint, (_, unit) in ENDPOINTS.items():
                fine_tuning = curves["fine_tuning"][budget][endpoint]
                scratch = curves["training_from_scratch"][budget][endpoint]
                winner = (
                    "fine_tuning"
                    if fine_tuning < scratch
                    else "training_from_scratch"
                    if scratch < fine_tuning
                    else "tie"
                )
                decisions.append(
                    {
                        "panel_id": (
                            f"{SOURCE_ID}:{system['material_system']}:n{budget}:{endpoint}"
                        ),
                        "material_system": system["material_system"],
                        "formula": system["formula"],
                        "composition_class": system["composition_class"],
                        "training_configuration_count": budget,
                        "endpoint": endpoint,
                        "outcome_unit": unit,
                        "fine_tuning_rmse": fine_tuning,
                        "training_from_scratch_rmse": scratch,
                        "winner": winner,
                        "fine_tuning_rmse_reduction_percent": (
                            100 * (scratch - fine_tuning) / scratch
                        ),
                    }
                )

    decisions.sort(key=lambda decision: decision["panel_id"])
    return {
        "artifact": "hwang_2026_surface_training_regime_panels_v1",
        "source_id": SOURCE_ID,
        "doi": DOI,
        "repository_revision": REPOSITORY_REVISION,
        "panel_count": len(decisions),
        "arm_count": 2 * len(decisions),
        "primary_outcome": "surface energy or force RMSE from exact Figure 2 source data",
        "normalization": (
            "negative RMSE, min-max normalized within material system, matched training "
            "configuration count, and endpoint"
        ),
        "matched_contract": {
            "matched_training_configuration_counts": matched_budgets,
            "common_surface_training_data_within_panel": True,
            "common_test_contract_within_panel": True,
        },
        "source_files": {
            **{
                f"data/{name}": {"sha256": metadata["sha256"]} for name, metadata in SYSTEMS.items()
            },
            **{name: {"sha256": digest} for name, digest in REPOSITORY_FILES.items()},
        },
        "interpretation_boundary": [
            "All outcomes come from exact released figure-source CSV files; "
            "no figure is digitized.",
            "Each panel matches the surface training configurations and evaluation "
            "endpoint while changing pretrained fine-tuning versus random initialization.",
            "The update regime changes within each panel, so these results test "
            "starting-model and training-regime compatibility rather than "
            "candidate-environment choice under one fixed trainer.",
            "The raw DFT datasets are not redistributed by the source repository, "
            "which prevents reconstruction of additional pre-training environment "
            "coordinates.",
            "The panels remain outside the strict fitted bridge and serve as an "
            "auxiliary training-regime audit.",
        ],
        "matched_decisions": decisions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(repository=args.repository)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
