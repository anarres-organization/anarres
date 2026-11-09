#!/usr/bin/env python3
"""Build a catalysis model-environment compatibility audit from exact tables."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "karimitari_2026_catalysis_finetuning"
DOI = "10.1038/s41524-026-02335-z"
ARXIV_ID = "2605.09394"
SOURCE_BUNDLE_SHA256 = "64fc864e4bdd5b047378c3647480136df6782da00929c1e5f6bb650edfcdf7f7"
MAIN_TEX_SHA256 = "0e22789d24394410fdb3bcad8a542909569498b8d4c93aa9edc5dfac6121752b"
SI_TEX_SHA256 = "7a673c05b2aca05b8cb1f82b8ab6880b3ee3a7d88d1d67778ffa26acb497df1e"

# Exact values from Tables 3 and 4 in submission_arxiv.tex. Missing outcomes
# remain missing rather than being reconstructed from figures.
MODELS = {
    "from_scratch": {
        "fs_bma": {
            "training_configuration_count": 39584,
            "components": ("relaxation",),
            "outcomes": {"reaction_energy_metal": 0.659},
        },
        "fs_bma_plus_md": {
            "training_configuration_count": 47651,
            "components": ("relaxation", "metal_md", "metal_oxide_md"),
            "outcomes": {
                "reaction_energy_metal": 0.310,
                "reaction_energy_metal_oxide": 0.476,
                "activation_barrier_metal": 0.398,
            },
        },
        "fs_all": {
            "training_configuration_count": 49860,
            "components": ("relaxation", "metal_md", "metal_oxide_md", "contour"),
            "outcomes": {
                "reaction_energy_metal": 0.279,
                "reaction_energy_metal_oxide": 0.398,
                "activation_barrier_metal": 0.175,
            },
        },
    },
    "fine_tuning": {
        "ft_bma": {
            "training_configuration_count": 39983,
            "components": ("relaxation",),
            "outcomes": {
                "reaction_energy_metal": 0.238,
                "reaction_energy_metal_oxide": 0.334,
                "activation_barrier_metal": 0.145,
            },
        },
        "ft_md_metal": {
            "training_configuration_count": 4976,
            "components": ("metal_md",),
            "outcomes": {
                "reaction_energy_metal": 0.376,
                "reaction_energy_metal_oxide": 0.428,
                "activation_barrier_metal": 0.149,
            },
        },
        "ft_md_metal_oxide": {
            "training_configuration_count": 2692,
            "components": ("metal_oxide_md",),
            "outcomes": {
                "reaction_energy_metal": 0.334,
                "reaction_energy_metal_oxide": 0.306,
                "activation_barrier_metal": 0.184,
            },
        },
        "ft_contour": {
            "training_configuration_count": 2208,
            "components": ("contour",),
            "outcomes": {
                "reaction_energy_metal": 0.421,
                "reaction_energy_metal_oxide": 0.305,
                "activation_barrier_metal": 0.139,
            },
        },
        "ft_bma_plus_md_metal": {
            "training_configuration_count": 44959,
            "components": ("relaxation", "metal_md"),
            "outcomes": {
                "reaction_energy_metal": 0.245,
                "reaction_energy_metal_oxide": 0.348,
                "activation_barrier_metal": 0.152,
            },
        },
        "ft_all": {
            "training_configuration_count": 49860,
            "components": ("relaxation", "metal_md", "metal_oxide_md", "contour"),
            "outcomes": {
                "reaction_energy_metal": 0.247,
                "reaction_energy_metal_oxide": 0.277,
                "activation_barrier_metal": 0.144,
            },
        },
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ingest(
    *,
    main_tex: Path | None = None,
    si_tex: Path | None = None,
    source_bundle: Path | None = None,
) -> dict:
    for path, expected in (
        (main_tex, MAIN_TEX_SHA256),
        (si_tex, SI_TEX_SHA256),
        (source_bundle, SOURCE_BUNDLE_SHA256),
    ):
        if path is not None and sha256(path) != expected:
            raise ValueError(f"checksum mismatch for {path.name}")

    panels = []
    arms = []
    endpoints = sorted(
        {
            endpoint
            for models in MODELS.values()
            for model in models.values()
            for endpoint in model["outcomes"]
        }
    )
    for regime, models in MODELS.items():
        for endpoint in endpoints:
            available = {
                name: model for name, model in models.items() if endpoint in model["outcomes"]
            }
            errors = [model["outcomes"][endpoint] for model in available.values()]
            best, worst = min(errors), max(errors)
            panel_id = f"{SOURCE_ID}:{regime}:{endpoint}"
            panels.append(
                {
                    "panel_id": panel_id,
                    "training_regime": regime,
                    "endpoint": endpoint,
                    "candidate_count": len(available),
                }
            )
            for environment, model in available.items():
                components = set(model["components"])
                value = model["outcomes"][endpoint]
                span = worst - best
                arms.append(
                    {
                        "source_id": SOURCE_ID,
                        "panel_id": panel_id,
                        "training_regime": regime,
                        "environment": environment,
                        "endpoint": endpoint,
                        "pre_outcome_measurements": {
                            "training_configuration_count": model["training_configuration_count"],
                            "common_omat_replay_configuration_count": (
                                30000 if regime == "fine_tuning" else 0
                            ),
                            "starts_from_mace_mh_1": int(regime == "fine_tuning"),
                            "contains_relaxation_configurations": int("relaxation" in components),
                            "contains_metal_md_configurations": int("metal_md" in components),
                            "contains_metal_oxide_md_configurations": int(
                                "metal_oxide_md" in components
                            ),
                            "contains_contour_bond_breaking_configurations": int(
                                "contour" in components
                            ),
                        },
                        "outcome": {"mean_absolute_error_eV": value},
                        "derived": {
                            "native_utility": -value,
                            "panel_normalized_utility": (
                                0.5 if span == 0 else (worst - value) / span
                            ),
                            "panel_normalized_regret": (
                                0.0 if span == 0 else (value - best) / span
                            ),
                        },
                    }
                )

    panels.sort(key=lambda panel: panel["panel_id"])
    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "karimitari_2026_catalysis_environment_compatibility_audit_v1",
        "source_id": SOURCE_ID,
        "doi": DOI,
        "source_version": f"arXiv:{ARXIV_ID}v1",
        "data_doi": "10.5281/zenodo.20043317",
        "panel_count": len(panels),
        "arm_count": len(arms),
        "primary_outcome": "reaction-energy or activation-barrier MAE in eV",
        "source_files": {
            "arXiv_source_bundle": {"sha256": SOURCE_BUNDLE_SHA256},
            "submission_arxiv.tex": {"sha256": MAIN_TEX_SHA256},
            "SI_arxiv.tex": {"sha256": SI_TEX_SHA256},
        },
        "panels": panels,
        "arms": arms,
        "interpretation_boundary": [
            "All outcomes come from exact manuscript tables; no figure is digitized.",
            "Candidate environments use different configuration counts, so these panels "
            "do not enter the matched-cost predictive bridge.",
            "Fine-tuning changes initialization, loss schedule, epoch count, and adds a "
            "common 30,000-configuration OMAT replay head relative to scratch training.",
            "The manuscript reports 39,584 configurations for FS-BMA in the outcome "
            "table and 39,983 for the underlying BMA dataset elsewhere. Each value is "
            "preserved only in its reported context.",
            "The release does not provide independent training-seed outcomes for these "
            "model comparisons.",
            "The audit tests model-environment compatibility and target dependence, not "
            "a fixed-trainer allocation rule.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-tex", type=Path)
    parser.add_argument("--si-tex", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(
        main_tex=args.main_tex,
        si_tex=args.si_tex,
        source_bundle=args.source_bundle,
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
