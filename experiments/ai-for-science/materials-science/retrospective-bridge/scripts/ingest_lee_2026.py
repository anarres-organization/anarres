#!/usr/bin/env python3
"""Build training-regime panels from Lee et al. (2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE_ID = "lee_2026_budget_constrained_augmentation"
DOI = "10.1038/s41524-026-02202-x"
REPOSITORY_REVISION = "f01ec6b8eab730ae5c09efa68b132fe3207878f3"
ARTICLE_REFERENCE_PDF_SHA256 = "3e1928a71969dac3300fd02315c863d692fd3d65fa7a089f4b005dcfab71bcfc"
SUPPLEMENTARY_PDF_SHA256 = "e328406669daac522a9fcc2cac6ca551e9889b4b21449d0bcb5ae566014c48af"

BASELINE = {
    "log_diffusivity_r2": 0.48,
    "bootstrap_log_diffusivity_r2_mean": 0.27,
    "bootstrap_log_diffusivity_r2_standard_deviation": 0.21,
}

METHODS = {
    "random": {
        "dft_label_budget": 8000,
        "uses_uniform_representation_coverage": 0,
        "uses_initial_aware_expansion": 0,
        "requires_structural_encoder": 0,
        "requires_iterative_distance_updates": 0,
    },
    "direct": {
        "dft_label_budget": 8879,
        "uses_uniform_representation_coverage": 1,
        "uses_initial_aware_expansion": 0,
        "requires_structural_encoder": 1,
        "requires_iterative_distance_updates": 0,
    },
    "lcmd": {
        "dft_label_budget": 8000,
        "uses_uniform_representation_coverage": 1,
        "uses_initial_aware_expansion": 1,
        "requires_structural_encoder": 1,
        "requires_iterative_distance_updates": 1,
    },
}

OUTCOMES = {
    "scratch": {
        "random": (15.93, 50.99, -0.0084, 0.20, 0.35, 0.22, 0.53, 0.59),
        "direct": (20.71, 60.68, 0.0235, 0.21, 0.42, 0.16, 0.26, 0.60),
        "lcmd": (20.38, 55.13, 0.0211, 0.20, 0.49, 0.15, 0.54, 0.70),
    },
    "fine_tuning": {
        "random": (20.69, 55.23, -0.0181, 0.21, 0.17, 0.28, 0.50, 0.40),
        "direct": (22.20, 66.42, 0.0322, 0.22, 0.40, 0.16, 0.48, 0.56),
        "lcmd": (20.12, 62.29, 0.0199, 0.20, 0.32, 0.18, 0.33, 0.53),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_revision(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def measurements(method: str, regime: str) -> dict:
    measured = dict(METHODS[method])
    measured.update(
        {
            "scratch_retraining": int(regime == "scratch"),
            "fine_tuning_with_replay_and_ewc": int(regime == "fine_tuning"),
            "label_budget_ratio_to_smallest_arm": measured["dft_label_budget"] / 8000,
        }
    )
    return measured


def native_outcome(values: tuple[float, ...]) -> dict:
    keys = (
        "mean_percentage_error_percent",
        "mean_absolute_percentage_error_percent",
        "mean_log_error_dex",
        "mean_absolute_log_error_dex",
        "bootstrap_log_diffusivity_r2_mean",
        "bootstrap_log_diffusivity_r2_standard_deviation",
        "linear_diffusivity_r2",
        "log_diffusivity_r2",
    )
    return dict(zip(keys, values, strict=True))


def ingest(
    *,
    repository: Path | None = None,
    article_reference_pdf: Path | None = None,
    supplementary_pdf: Path | None = None,
) -> dict:
    if repository is not None and repository_revision(repository) != REPOSITORY_REVISION:
        raise ValueError("unexpected MLIP-sampling-strategy repository revision")
    if (
        article_reference_pdf is not None
        and sha256(article_reference_pdf) != ARTICLE_REFERENCE_PDF_SHA256
    ):
        raise ValueError("checksum mismatch for the article reference PDF")
    if supplementary_pdf is not None and sha256(supplementary_pdf) != SUPPLEMENTARY_PDF_SHA256:
        raise ValueError("checksum mismatch for the supplementary PDF")

    arms = []
    for regime, regime_outcomes in OUTCOMES.items():
        panel_id = f"{SOURCE_ID}:sodium_oxide:{regime}:log_diffusivity_r2"
        panel_arms = []
        for method, values in regime_outcomes.items():
            outcome = native_outcome(values)
            budget = METHODS[method]["dft_label_budget"]
            improvement = outcome["log_diffusivity_r2"] - BASELINE["log_diffusivity_r2"]
            panel_arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "material_system": "sodium_oxide_solid_electrolytes",
                    "training_regime": regime,
                    "endpoint": "log10_sodium_ion_diffusivity_r2",
                    "environment": method,
                    "pre_outcome_measurements": measurements(method, regime),
                    "outcome": outcome,
                    "derived": {
                        "improvement_over_matpes_r2": improvement,
                        "improvement_over_matpes_r2_per_1000_labels": improvement / (budget / 1000),
                    },
                }
            )

        raw = [arm["outcome"]["log_diffusivity_r2"] for arm in panel_arms]
        efficient = [
            arm["derived"]["improvement_over_matpes_r2_per_1000_labels"] for arm in panel_arms
        ]
        for values, prefix in ((raw, "panel"), (efficient, "cost_adjusted")):
            best, worst = max(values), min(values)
            span = best - worst
            for arm, value in zip(panel_arms, values, strict=True):
                arm["derived"][f"{prefix}_normalized_utility"] = (
                    0.5 if span == 0 else (value - worst) / span
                )
                arm["derived"][f"{prefix}_normalized_regret"] = (
                    0.0 if span == 0 else (best - value) / span
                )
        arms.extend(panel_arms)

    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "lee_2026_training_regime_panels_v1",
        "source_id": SOURCE_ID,
        "doi": DOI,
        "repository_revision": REPOSITORY_REVISION,
        "panel_count": 2,
        "arm_count": 6,
        "primary_outcome": "log10 sodium-ion diffusivity R2 from Supplementary Table S2",
        "baseline": BASELINE,
        "normalization": (
            "raw R2 and improvement over the MatPES baseline per 1,000 DFT labels are "
            "min-max normalized separately within each training regime"
        ),
        "source_files": {
            "article_reference_pdf": {"sha256": ARTICLE_REFERENCE_PDF_SHA256},
            "supplementary_information_pdf": {"sha256": SUPPLEMENTARY_PDF_SHA256},
        },
        "interpretation_boundary": [
            "Exact numerical outcomes come from Supplementary Table S2; figures are not digitized.",
            "Random and LCMD use 8,000 DFT labels, while DIRECT uses 8,879. The paper "
            "describes these as matched or comparable budgets, but they are not exactly equal.",
            "A cost-normalized improvement sensitivity preserves the raw winners: LCMD after "
            "scratch retraining and DIRECT after fine-tuning.",
            "The two panels remain an auxiliary regime audit rather than entering the strict "
            "matched-cost fitted bridge.",
            "The public repository is a reduced reproducibility example rather than the "
            "claim-bearing numerical result archive.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--article-reference-pdf", type=Path)
    parser.add_argument("--supplementary-pdf", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(
        repository=args.repository,
        article_reference_pdf=args.article_reference_pdf,
        supplementary_pdf=args.supplementary_pdf,
    )
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
