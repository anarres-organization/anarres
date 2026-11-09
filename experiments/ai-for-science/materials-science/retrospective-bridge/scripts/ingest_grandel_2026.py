#!/usr/bin/env python3
"""Build phonon training-environment panels from Grandel et al. (2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "grandel_2026_phonon_finetuning"
ARXIV_ID = "2604.01017"
SOURCE_BUNDLE_SHA256 = "b0053b8914d66d23862ae5792e40191b5164cbbfde3a3d733681a000aeb7f501"
RESULTS_TEX_SHA256 = "129f83fbe79038385a9160ab7ea8cedd40474be21a27230d0ce28068abdc0242"

# Exact median phonon MAE and interquartile range from Table 1 in results.tex.
TABLE = {
    "training_from_scratch": {
        "primitive_cell": (0.39, 0.50),
        "small_supercell": (0.25, 0.39),
        "large_supercell": (0.21, 0.14),
    },
    "transfer_learning": {
        "primitive_cell": (0.12, 0.07),
        "small_supercell": (0.09, 0.06),
        "large_supercell": (0.06, 0.05),
    },
    "multihead_fine_tuning": {
        "primitive_cell": (0.18, 0.16),
        "small_supercell": (0.12, 0.06),
        "large_supercell": (0.07, 0.06),
    },
    "equitrain": {
        "primitive_cell": (0.12, 0.12),
        "small_supercell": (0.07, 0.06),
        "large_supercell": (0.05, 0.05),
    },
}

ENVIRONMENTS = {
    "primitive_cell": {
        "maximum_supercell_edge_A": None,
        "larger_than_primitive_cell": 0,
    },
    "small_supercell": {
        "maximum_supercell_edge_A": 10,
        "larger_than_primitive_cell": 1,
    },
    "large_supercell": {
        "maximum_supercell_edge_A": 15,
        "larger_than_primitive_cell": 1,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(*, results_tex: Path | None = None, source_bundle: Path | None = None) -> dict:
    if results_tex is not None and sha256(results_tex) != RESULTS_TEX_SHA256:
        raise ValueError("checksum mismatch for results.tex")
    if source_bundle is not None and sha256(source_bundle) != SOURCE_BUNDLE_SHA256:
        raise ValueError("checksum mismatch for the arXiv source bundle")

    arms = []
    for regime, environments in TABLE.items():
        panel_id = f"{SOURCE_ID}:53_materials:{regime}:phonon_frequency_mae"
        errors = [values[0] for values in environments.values()]
        best, worst = min(errors), max(errors)
        span = worst - best
        for environment, (median, iqr) in environments.items():
            arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "evaluation_set": "53_materials",
                    "training_regime": regime,
                    "training_environment": environment,
                    "training_configuration_count_per_material": 10,
                    "pre_outcome_measurements": {
                        **ENVIRONMENTS[environment],
                        "training_configuration_count_per_material": 10,
                    },
                    "outcome": {
                        "median_phonon_frequency_mae_THz": median,
                        "interquartile_range_THz": iqr,
                    },
                    "derived": {
                        "native_utility": -median,
                        "panel_normalized_utility": (0.5 if span == 0 else (worst - median) / span),
                        "panel_normalized_regret": (0.0 if span == 0 else (median - best) / span),
                    },
                }
            )

    arms.sort(key=lambda arm: (arm["panel_id"], arm["training_environment"]))
    return {
        "artifact": "grandel_2026_phonon_training_environment_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": f"arXiv:{ARXIV_ID}",
        "data_doi": "10.5281/zenodo.22180297",
        "panel_count": 4,
        "arm_count": 12,
        "primary_outcome": ("median phonon-frequency MAE across 53 material-specific models"),
        "normalization": ("negative median MAE, min-max normalized within each adaptation regime"),
        "source_files": {
            "arXiv_source_bundle": {"sha256": SOURCE_BUNDLE_SHA256},
            "results.tex": {"sha256": RESULTS_TEX_SHA256},
        },
        "interpretation_boundary": [
            "The exact values come from Table 1 in the released arXiv source; "
            "no figure is digitized.",
            "Every arm uses ten configurations per material, but larger supercells "
            "contain more atoms and require more DFT compute. Configuration count "
            "is therefore not an equal reference-label cost.",
            "Each outcome is a median over 53 material-specific models. The table "
            "does not release a complete material-level matrix for this comparison.",
            "The panels remain outside the strict matched-cost fitted bridge and "
            "serve as a cost-sensitive environment audit.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-tex", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(results_tex=args.results_tex, source_bundle=args.source_bundle)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
