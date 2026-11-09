#!/usr/bin/env python3
"""Build matched thermodynamic-coverage panels from Kim et al. (2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

SOURCE_ID = "kim_2026_density_diversity"
ARXIV_ID = "2605.05733v1"
REPOSITORY_REVISION = "911342978ec687673ecfa76d47729b6feb7dad8b"
SOURCE_BUNDLE_SHA256 = "29a7808013f4a2cc2ab6df65d79928330b2c71ecd6ceadad03e2773efbf5d2bc"
PAPER_TEX_SHA256 = "f49d278a3607d3b78bec5fe181a22582a7d540b41fedb6efb77e90c5c9605520"
SEEDS = (19970928, 493423, 677233, 765427, 851482)
TEMPERATURES_K = (300, 500, 700, 900)
DENSITIES = {"03": 0.3, "06": 0.6, "10": 1.0}
ENVIRONMENTS = {
    "no_variance": {
        "directory": "NVar",
        "training_temperatures_K": (700,),
        "training_densities_g_cm3": (1.0,),
    },
    "temperature_diverse": {
        "directory": "TVar",
        "training_temperatures_K": (700, 900),
        "training_densities_g_cm3": (1.0,),
    },
    "density_diverse": {
        "directory": "DVar",
        "training_temperatures_K": (700,),
        "training_densities_g_cm3": (0.3, 1.0),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_revision(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def rdf_similarity(test_file: Path, reference_file: Path) -> float:
    """Evaluate Equation 1 on the released radial grids.

    Four seed releases use bin centers while the reference and first seed use
    grid endpoints. Interpolating the reference to each released test grid
    preserves the test trajectory and avoids treating a half-bin offset as a
    physical RDF discrepancy.
    """
    with np.load(test_file) as test, np.load(reference_file) as reference:
        radii = np.asarray(test["radii"], dtype=float)
        test_rdf = np.asarray(test["rdf"], dtype=float)
        reference_rdf = np.interp(radii, reference["radii"], reference["rdf"])
    numerator = np.trapezoid(np.abs(test_rdf - reference_rdf), radii)
    denominator = np.trapezoid(np.abs(test_rdf - 1.0), radii) + np.trapezoid(
        np.abs(reference_rdf - 1.0), radii
    )
    if denominator <= 0:
        raise ValueError(f"non-positive RDF normalization for {test_file}")
    return float(1.0 - numerator / denominator)


def measurements(environment: str, target_temperature_K: int, target_density: float) -> dict:
    contract = ENVIRONMENTS[environment]
    temperatures = contract["training_temperatures_K"]
    densities = contract["training_densities_g_cm3"]
    temperature_gap = min(abs(target_temperature_K - value) for value in temperatures)
    density_gap = min(abs(target_density - value) for value in densities)
    return {
        "training_density_span_g_cm3": max(densities) - min(densities),
        "training_temperature_span_K": max(temperatures) - min(temperatures),
        "closest_density_gap_g_cm3": density_gap,
        "closest_temperature_gap_K": temperature_gap,
        "target_density_inside_training_range": int(
            min(densities) <= target_density <= max(densities)
        ),
        "target_temperature_inside_training_range": int(
            min(temperatures) <= target_temperature_K <= max(temperatures)
        ),
        "training_configuration_count": 512,
    }


def training_configuration_count(root: Path, directory: str) -> int:
    files = sorted((root / "h2o_distilled_train_database" / directory).glob("*.extxyz"))
    if len(files) != 2:
        raise ValueError(f"expected two training files for {directory}")
    return sum(path.read_text(encoding="utf-8").count("\nLattice=") + int(
        path.read_text(encoding="utf-8").startswith("Lattice=")
    ) for path in files)


def ingest(
    *,
    source_root: Path,
    paper_tex: Path | None = None,
    source_bundle: Path | None = None,
) -> dict:
    if repository_revision(source_root) != REPOSITORY_REVISION:
        raise ValueError("unexpected MLFFTrans repository revision")
    if paper_tex is not None and sha256(paper_tex) != PAPER_TEX_SHA256:
        raise ValueError("checksum mismatch for main.tex")
    if source_bundle is not None and sha256(source_bundle) != SOURCE_BUNDLE_SHA256:
        raise ValueError("checksum mismatch for the arXiv source bundle")
    for contract in ENVIRONMENTS.values():
        if training_configuration_count(source_root, contract["directory"]) != 512:
            raise ValueError("training environments do not have the matched 512-frame budget")

    arms = []
    for temperature in TEMPERATURES_K:
        for density_label, density in DENSITIES.items():
            panel_id = f"{SOURCE_ID}:h2o:T{temperature}:rho{density_label}:rdf_similarity"
            reference = (
                source_root
                / "h2o_distilled_structure"
                / "REF"
                / f"T{temperature}_rho{density_label}.npz"
            )
            panel_arms = []
            for environment, contract in ENVIRONMENTS.items():
                seed_scores = []
                for seed in SEEDS:
                    test_file = (
                        source_root
                        / "SeedEnsemble"
                        / "data"
                        / f"SEED{seed}"
                        / contract["directory"]
                        / f"T{temperature}"
                        / f"rho{density_label}"
                        / "rdf_OO.npz"
                    )
                    seed_scores.append(rdf_similarity(test_file, reference))
                panel_arms.append(
                    {
                        "source_id": SOURCE_ID,
                        "panel_id": panel_id,
                        "material_system": "h2o",
                        "evaluation_temperature_K": temperature,
                        "evaluation_density_g_cm3": density,
                        "endpoint": "oxygen_oxygen_rdf_similarity",
                        "environment": environment,
                        "pre_outcome_measurements": measurements(environment, temperature, density),
                        "outcome": {
                            "mean_rdf_similarity": float(np.mean(seed_scores)),
                            "rdf_similarity_standard_deviation": float(
                                np.std(seed_scores, ddof=1)
                            ),
                            "seed_scores": [float(value) for value in seed_scores],
                            "independent_training_seeds": len(seed_scores),
                        },
                    }
                )
            scores = [arm["outcome"]["mean_rdf_similarity"] for arm in panel_arms]
            best, worst = max(scores), min(scores)
            span = best - worst
            for arm, score in zip(panel_arms, scores, strict=True):
                arm["derived"] = {
                    "native_utility": score,
                    "panel_normalized_utility": 0.5 if span == 0 else (score - worst) / span,
                    "panel_normalized_regret": 0.0 if span == 0 else (best - score) / span,
                }
            arms.extend(panel_arms)

    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "kim_2026_density_diversity_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": f"arXiv:{ARXIV_ID}",
        "repository_revision": REPOSITORY_REVISION,
        "panel_count": len({arm["panel_id"] for arm in arms}),
        "arm_count": len(arms),
        "primary_outcome": "five-seed mean RDF similarity from Equation 1",
        "normalization": "RDF similarity min-max normalized within each thermodynamic state",
        "matched_contract": {
            "training_configuration_count": 512,
            "training_seeds": list(SEEDS),
            "common_reference_within_panel": True,
            "student_architecture": "SevenNet lmax=1 with two convolutional layers",
        },
        "source_files": {
            "arXiv_source_bundle": {"sha256": SOURCE_BUNDLE_SHA256},
            "main.tex": {"sha256": PAPER_TEX_SHA256},
        },
        "interpretation_boundary": [
            "The bridge reconstructs Equation 1 from exact released RDF arrays "
            "and does not digitize figures.",
            "The source repository was updated after the arXiv manuscript with five "
            "explicit training seeds; the pinned revision is treated as a public "
            "robustness release.",
            "A half-bin radial-grid change among seed releases is handled by "
            "interpolating the common reference RDF onto each released test grid.",
            "All three environments contain 512 configurations and use the same "
            "student architecture, optimization contract, teacher labels, and "
            "thermodynamic evaluation states.",
            "The three environments change the density or temperature support of "
            "the training data, not one isolated causal factor in the generated "
            "trajectories.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--paper-tex", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(
        source_root=args.source_root,
        paper_tex=args.paper_tex,
        source_bundle=args.source_bundle,
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
