#!/usr/bin/env python3
"""Build matched panels from the exact tables in Wang et al. (2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "wang_2026_dataset_aware_entropy"
ARXIV_ID = "2605.20384"
SOURCE_BUNDLE_SHA256 = "0ca4daf9c9c8249edffb1cc94f433e9005517c5ade86bd50c8df01e2db532041"
PAPER_TEX_SHA256 = "83831cbe107889ad4ee0156427cddca005982edc69dbdf540b6c1691e1edc612"

# Exact mean and one-standard-deviation entries from Tables 1--3. Carbon
# force values retain the source table's eV/A unit; silicon and NaCl use
# meV/A. Units never mix within a decision panel.
IN_DISTRIBUTION = {
    "carbon": {
        100: {
            "energy": ((12.5, 0.7), (58.2, 0.4)),
            "force": ((0.209, 0.003), (0.258, 0.002)),
            "stress": ((2.36, 0.13), (4.76, 0.23)),
        },
        250: {
            "energy": ((8.9, 0.8), (51.6, 7.0)),
            "force": ((0.171, 0.006), (0.261, 0.004)),
            "stress": ((2.53, 0.07), (4.32, 0.35)),
        },
        500: {
            "energy": ((5.9, 0.5), (43.3, 1.6)),
            "force": ((0.131, 0.001), (0.269, 0.004)),
            "stress": ((2.45, 0.08), (3.92, 0.23)),
        },
        800: {
            "energy": ((4.2, 0.2), (42.8, 1.0)),
            "force": ((0.084, 0.003), (0.268, 0.004)),
            "stress": ((2.42, 0.09), (3.75, 0.21)),
        },
    },
    "silicon": {
        100: {
            "energy": ((2.49, 0.15), (4.17, 0.60)),
            "force": ((25.7, 0.6), (25.8, 2.3)),
            "stress": ((0.39, 0.04), (0.54, 0.03)),
        },
        250: {
            "energy": ((2.09, 0.43), (4.19, 0.70)),
            "force": ((23.7, 1.7), (23.5, 0.2)),
            "stress": ((0.38, 0.03), (0.57, 0.02)),
        },
        500: {
            "energy": ((1.59, 0.22), (4.03, 0.34)),
            "force": ((21.1, 0.6), (22.6, 0.2)),
            "stress": ((0.35, 0.02), (0.57, 0.01)),
        },
        800: {
            "energy": ((1.32, 0.08), (3.81, 0.29)),
            "force": ((20.0, 0.2), (22.5, 0.2)),
            "stress": ((0.33, 0.01), (0.56, 0.01)),
        },
    },
    "nacl": {
        100: {
            "energy": ((0.54, 0.14), (1.82, 0.05)),
            "force": ((6.0, 1.6), (27.5, 1.0)),
            "stress": ((0.07, 0.01), (0.22, 0.00)),
        },
        250: {
            "energy": ((0.48, 0.01), (2.40, 0.25)),
            "force": ((4.1, 0.1), (32.4, 1.7)),
            "stress": ((0.06, 0.00), (0.21, 0.01)),
        },
        500: {
            "energy": ((0.47, 0.01), (2.48, 0.28)),
            "force": ((4.1, 0.1), (34.2, 2.1)),
            "stress": ((0.06, 0.00), (0.18, 0.00)),
        },
        800: {
            "energy": ((0.44, 0.01), (2.59, 0.17)),
            "force": ((4.2, 0.04), (34.7, 1.4)),
            "stress": ((0.06, 0.00), (0.19, 0.01)),
        },
    },
}

# Exact N=800 entries from Table 4 on separately constructed equilibrium and
# thermal-MD test sets.
INDEPENDENT_TEST = {
    "carbon": {
        "energy": ((6.4, 0.4), (10.2, 0.7)),
        "force": ((61.9, 0.5), (40.5, 1.0)),
        "stress": ((2.05, 0.10), (1.30, 0.03)),
    },
    "silicon": {
        "energy": ((1.80, 0.06), (2.52, 0.10)),
        "force": ((34.2, 0.2), (33.1, 0.0)),
        "stress": ((0.20, 0.00), (0.28, 0.00)),
    },
    "nacl": {
        "energy": ((0.70, 0.05), (3.19, 0.07)),
        "force": ((7.6, 0.0), (11.7, 0.2)),
        "stress": ((0.07, 0.00), (0.08, 0.01)),
    },
}

UNITS = {
    ("carbon", "force", "in_distribution"): "eV_per_A",
    ("carbon", "force", "independent_test"): "meV_per_A",
}
DEFAULT_UNITS = {"energy": "meV_per_atom", "force": "meV_per_A", "stress": "GPa"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def measurements(environment: str, distribution: str, budget: int) -> dict:
    entropy = environment == "entropy_driven"
    # The in-distribution holdout is sampled from the entropy pool. The
    # independent test emphasizes equilibrium and thermal MD, which is closer
    # to the random-MD generator. This match is determined by construction,
    # not by the downstream errors.
    target_match = entropy if distribution == "in_distribution" else not entropy
    return {
        "uses_dataset_entropy": int(entropy),
        "uses_structural_coverage_selection": int(entropy),
        "targets_underrepresented_structure_space": int(entropy),
        "target_distribution_match": int(target_match),
        "adaptive_acquisition": int(entropy),
        "training_configuration_count": budget,
    }


def build_panel(
    *,
    system: str,
    distribution: str,
    budget: int,
    endpoint: str,
    values: tuple[tuple[float, float], tuple[float, float]],
) -> list[dict]:
    panel_id = f"{SOURCE_ID}:{system}:{distribution}:n{budget}:{endpoint}_mae"
    arms = []
    for environment, (mean, standard_deviation) in zip(
        ("entropy_driven", "random_md"), values, strict=True
    ):
        arms.append(
            {
                "source_id": SOURCE_ID,
                "panel_id": panel_id,
                "material_system": system,
                "evaluation_distribution": distribution,
                "endpoint": endpoint,
                "outcome_unit": UNITS.get(
                    (system, endpoint, distribution), DEFAULT_UNITS[endpoint]
                ),
                "training_configuration_count": budget,
                "environment": environment,
                "pre_outcome_measurements": measurements(environment, distribution, budget),
                "outcome": {
                    "mean_mae": mean,
                    "mae_standard_deviation": standard_deviation,
                    "independent_training_draws": 3,
                },
            }
        )
    errors = [arm["outcome"]["mean_mae"] for arm in arms]
    best, worst = min(errors), max(errors)
    span = worst - best
    for arm, error in zip(arms, errors, strict=True):
        arm["derived"] = {
            "native_utility": -error,
            "panel_normalized_utility": 0.5 if span == 0 else (worst - error) / span,
            "panel_normalized_regret": 0.0 if span == 0 else (error - best) / span,
        }
    return arms


def ingest(*, paper_tex: Path | None = None, source_bundle: Path | None = None) -> dict:
    if paper_tex is not None and sha256(paper_tex) != PAPER_TEX_SHA256:
        raise ValueError("checksum mismatch for paper.tex")
    if source_bundle is not None and sha256(source_bundle) != SOURCE_BUNDLE_SHA256:
        raise ValueError("checksum mismatch for the arXiv source bundle")

    arms = []
    for system, budgets in IN_DISTRIBUTION.items():
        for budget, endpoints in budgets.items():
            for endpoint, values in endpoints.items():
                arms.extend(
                    build_panel(
                        system=system,
                        distribution="in_distribution",
                        budget=budget,
                        endpoint=endpoint,
                        values=values,
                    )
                )
    for system, endpoints in INDEPENDENT_TEST.items():
        for endpoint, values in endpoints.items():
            arms.extend(
                build_panel(
                    system=system,
                    distribution="independent_test",
                    budget=800,
                    endpoint=endpoint,
                    values=values,
                )
            )
    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "wang_2026_dataset_aware_entropy_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": "arXiv:2605.20384v1",
        "panel_count": len({arm["panel_id"] for arm in arms}),
        "arm_count": len(arms),
        "primary_outcome": "three-draw mean energy, force, or stress MAE",
        "normalization": (
            "negative MAE, min-max normalized within system, test distribution, "
            "budget, and endpoint"
        ),
        "matched_contract": {
            "training_configuration_counts": [100, 250, 500, 800],
            "training_draw_seeds": [42, 123, 456],
            "common_validation_and_test_partition_within_panel": True,
        },
        "source_files": {
            "arXiv_source_bundle": {"sha256": SOURCE_BUNDLE_SHA256},
            "paper.tex": {"sha256": PAPER_TEX_SHA256},
        },
        "interpretation_boundary": [
            "The bridge uses only exact numerical entries from Tables 1--4 and "
            "does not digitize learning-curve figures.",
            "The in-distribution test partition is drawn from the entropy-driven "
            "pool, while the independent test emphasizes equilibrium and thermal-MD "
            "configurations.",
            "The post-outcome carbon mixed-pool remedy is excluded because its "
            "composition was designed after observing the independent-test reversal.",
            "Three reported draws combine training-subset and optimizer variation; "
            "individual seed outcomes are not released in the source tables.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-tex", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(paper_tex=args.paper_tex, source_bundle=args.source_bundle)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
