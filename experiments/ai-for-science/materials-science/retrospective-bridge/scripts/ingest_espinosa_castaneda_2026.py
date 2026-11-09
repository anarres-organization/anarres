#!/usr/bin/env python3
"""Reconstruct matched acquisition-policy panels from the diversity study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

SOURCE_ID = "espinosa_castaneda_2026_diversity"
REPOSITORY_REVISION = "9c3098d17222f9796851bc35276136a007bcd61d"
ARCHIVE_MD5 = "92518bb6907804fbf682914abb753b4c"
ARCHIVE_SHA256 = "2e591e0af2d0369ad6ff28956333bb139eb50b47ba135a4d1f974652c3724d8a"
SEEDS = tuple(str(seed) for seed in range(5))
MODELS = ("rf", "xgb")

DFT_TARGETS = {
    "bandgap": ("bandgap",),
    "bulk_modulus": ("bulk_modulus",),
    "e_form": ("e_form",),
    "bandgap_bulkmodulus": ("bandgap", "bulk_modulus"),
    "bandgap_eform": ("bandgap", "e_form"),
    "eform_bulk_modulus": ("e_form", "bulk_modulus"),
}
EXPERIMENTAL_TARGETS = {
    "electric_cond": ("electric_cond",),
    "seebeck_coef": ("seebeck_coef",),
    "thermal_cond": ("thermal_cond",),
    "zT": ("zT",),
    "el_seeb": ("electric_cond", "seebeck_coef"),
    "el_ThC": ("electric_cond", "thermal_cond"),
    "el_zT": ("electric_cond", "zT"),
    "seeb_ThC": ("seebeck_coef", "thermal_cond"),
    "seeb_zT": ("seebeck_coef", "zT"),
    "zT_ThC": ("zT", "thermal_cond"),
    "el_seeb_zT": ("electric_cond", "seebeck_coef", "zT"),
    "el_seeb_ThC": ("electric_cond", "seebeck_coef", "thermal_cond"),
    "el_zT_ThC": ("electric_cond", "zT", "thermal_cond"),
    "seeb_zT_ThC": ("seebeck_coef", "zT", "thermal_cond"),
}
DFT_METRICS = {
    "bandgap": ("rmse_bandgap",),
    "bulk_modulus": ("rmse_bulk_modulus",),
    "e_form": ("rmse_e_form", "rmse_eform"),
}
EXPERIMENTAL_METRICS = {
    "electric_cond": ("rmse_elec_cond",),
    "seebeck_coef": ("rmse_seebeck",),
    "thermal_cond": ("rmse_k_total",),
    "zT": ("rmse_zt",),
}

# These are the policy families with five released seeds for every dataset and
# target combination at the corresponding target count. Supplementary methods
# with incomplete target coverage remain outside the matched bridge.
DFT_POLICIES = {
    1: {
        "random": "random",
        "qbc": "QBC",
        "hv_kmedoids": "grow_disagreementHV_topM_kmedoids_OneTarget",
        "ts_disagreement": "grow_TS_QBC_no_diversity_OneTarget",
        "dpp_ts_disagreement": "grow_DPP_TS_QBC_OneTarget",
        "nsga_disagreement_diversity": "grow_EA_QBC_1Obj_withDiversity",
    },
    2: {
        "random": "random",
        "qbc": "grow2QBC",
        "ts_disagreement": "grow_TS_QBC_no_diversity_TwoTargets",
        "dpp_ts_disagreement": "grow_DPP_TS_QBC_TwoTargets",
        "nsga_disagreement": "growing_EA_2obj_qbc_only",
        "nsga_disagreement_diversity": "grow_EA_QBC_2Obj_twoTargets_plusDiversity",
    },
}
EXPERIMENTAL_POLICIES = {
    1: {
        "random": "grow_random",
        "qbc": "grow_QBC",
        "ts_disagreement": "grow_TS_QBC_no_diversity_OneTarget",
        "dpp_ts_disagreement": "grow_DPP_TS_QBC_OneTarget",
        "nsga_disagreement_diversity": "grow_EA_DeltaDiversity",
    },
    2: {
        "random": "grow_random",
        "qbc": "grow_2QBC",
        "ts_disagreement": "grow_TS_QBC_no_diversity_TwoTargets",
        "dpp_ts_disagreement": "grow_DPP_TS_QBC_TwoTargets",
        "nsga_disagreement": "grow_EA_2Obj_TwoTargets_QBC_ONLY",
        "nsga_disagreement_diversity": "grow_EA_3Obj_TwoTargets",
    },
    3: {
        "random": "grow_random",
        "qbc": "grow_3QBC",
        "ts_disagreement": "grow_TS_QBC_no_diversity_ThreeTargets",
        "dpp_ts_disagreement": "grow_DPP_TS_QBC_ThreeTargets",
        "nsga_disagreement": "grow_EA_3Obj_ThreeTargets_QBC_ONLY",
        "nsga_disagreement_diversity": "grow_EA_4Obj_ThreeTargets",
    },
}

POLICY_COORDINATES = {
    "random": (0, 0, 0, 0),
    "qbc": (1, 0, 0, 1),
    "hv_kmedoids": (1, 0, 1, 1),
    "ts_disagreement": (1, 1, 0, 1),
    "dpp_ts_disagreement": (1, 1, 1, 1),
    "nsga_disagreement": (1, 1, 0, 1),
    "nsga_disagreement_diversity": (1, 1, 1, 1),
}


def file_hash(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _curve(path: Path, metric_names: tuple[str, ...]) -> tuple[float, int, int, int, float, float]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty result curve: {path}")
    metric = next((name for name in metric_names if name in rows[0]), None)
    if metric is None:
        raise ValueError(f"missing RMSE metric {metric_names}: {path}")

    by_fraction: dict[float, list[float]] = defaultdict(list)
    train_sizes: dict[float, list[int]] = defaultdict(list)
    for row in rows:
        fraction = float(row["train_ratio"])
        by_fraction[fraction].append(float(row[metric]))
        train_sizes[fraction].append(int(float(row["train_size"])))
    points = sorted((fraction, statistics.fmean(by_fraction[fraction])) for fraction in by_fraction)
    if len(points) < 2:
        raise ValueError(f"fewer than two curve points: {path}")
    width = points[-1][0] - points[0][0]
    area = sum(
        (right_x - left_x) * (left_y + right_y) / 2.0
        for (left_x, left_y), (right_x, right_y) in zip(points, points[1:], strict=False)
    )
    first_fraction, last_fraction = points[0][0], points[-1][0]
    first_size = round(statistics.fmean(train_sizes[first_fraction]))
    last_size = round(statistics.fmean(train_sizes[last_fraction]))
    return area / width, len(points), first_size, last_size, first_fraction, last_fraction


def _result_file(
    root: Path,
    *,
    policy_directory: str,
    dataset: str,
    target: str,
    seed: str,
    model: str,
    random_directory: str,
) -> Path:
    actual_target = "all" if policy_directory == random_directory else target
    directory = root / policy_directory / dataset / actual_target / seed
    matches = [
        path
        for path in directory.glob("*.csv")
        if "trainIndices" not in path.name and f"_{model}" in path.name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one result for {policy_directory}/{dataset}/{actual_target}/"
            f"{seed}/{model}, found {len(matches)}"
        )
    return matches[0]


def _measurements(
    policy: str,
    *,
    target_count: int,
    targets_evaluation_property: bool,
    first_training_count: int,
    last_training_fraction: float,
) -> dict:
    uses_disagreement, outcome_diversity, feature_diversity, adaptive = POLICY_COORDINATES[policy]
    uses_target_objective = policy != "random"
    return {
        "uses_model_disagreement": uses_disagreement,
        "uses_outcome_disagreement_diversity": outcome_diversity,
        "uses_feature_space_diversity": feature_diversity,
        "adaptive_acquisition": adaptive,
        "targets_evaluation_property": int(uses_target_objective and targets_evaluation_property),
        "target_property_count": target_count if uses_target_objective else 0,
        "initial_training_count": first_training_count,
        "final_training_fraction": last_training_fraction,
    }


def _build_family(
    root: Path,
    *,
    family: str,
    targets: dict[str, tuple[str, ...]],
    metrics: dict[str, tuple[str, ...]],
    policies: dict[int, dict[str, str]],
    random_directory: str,
) -> list[dict]:
    datasets = sorted(path.name for path in (root / random_directory).iterdir() if path.is_dir())
    arms: list[dict] = []
    for dataset in datasets:
        for target_id, targeted_properties in targets.items():
            target_count = len(targeted_properties)
            candidate_policies = policies[target_count]
            for model in MODELS:
                random_curves = {}
                for evaluation_property, metric_names in metrics.items():
                    random_curves[evaluation_property] = [
                        _curve(
                            _result_file(
                                root,
                                policy_directory=random_directory,
                                dataset=dataset,
                                target=target_id,
                                seed=seed,
                                model=model,
                                random_directory=random_directory,
                            ),
                            metric_names,
                        )
                        for seed in SEEDS
                    ]

                for evaluation_property, metric_names in metrics.items():
                    panel_id = (
                        f"{SOURCE_ID}:{family}:{dataset}:{target_id}:{model}:"
                        f"{evaluation_property}:rmse_auc"
                    )
                    random_aucs = [value[0] for value in random_curves[evaluation_property]]
                    panel_arms = []
                    for policy, directory in candidate_policies.items():
                        curves = [
                            _curve(
                                _result_file(
                                    root,
                                    policy_directory=directory,
                                    dataset=dataset,
                                    target=target_id,
                                    seed=seed,
                                    model=model,
                                    random_directory=random_directory,
                                ),
                                metric_names,
                            )
                            for seed in SEEDS
                        ]
                        aucs = [value[0] for value in curves]
                        improvements = [
                            100.0 * (1.0 - auc / random_auc)
                            for auc, random_auc in zip(aucs, random_aucs, strict=True)
                        ]
                        initial_counts = {value[2] for value in curves}
                        final_counts = {value[3] for value in curves}
                        point_counts = {value[1] for value in curves}
                        first_fractions = {value[4] for value in curves}
                        last_fractions = {value[5] for value in curves}
                        if any(
                            len(values) != 1
                            for values in (initial_counts, final_counts, last_fractions)
                        ):
                            raise ValueError(
                                f"unmatched acquisition contract in {panel_id}/{policy}"
                            )
                        is_targeted = evaluation_property in targeted_properties
                        panel_arms.append(
                            {
                                "source_id": SOURCE_ID,
                                "panel_id": panel_id,
                                "data_regime": family,
                                "dataset": dataset,
                                "target_set": target_id,
                                "targeted_properties": list(targeted_properties),
                                "evaluation_property": evaluation_property,
                                "evaluation_property_is_targeted": is_targeted,
                                "downstream_model": model,
                                "environment": policy,
                                "pre_outcome_measurements": _measurements(
                                    policy,
                                    target_count=target_count,
                                    targets_evaluation_property=is_targeted,
                                    first_training_count=next(iter(initial_counts)),
                                    last_training_fraction=next(iter(last_fractions)),
                                ),
                                "outcome": {
                                    "mean_normalized_rmse_auc": statistics.fmean(aucs),
                                    "rmse_auc_sd_across_seeds": statistics.stdev(aucs),
                                    "mean_percent_improvement_vs_paired_random": (
                                        statistics.fmean(improvements)
                                    ),
                                    "improvement_sd_across_seeds": statistics.stdev(improvements),
                                    "independent_campaign_seeds": len(SEEDS),
                                    "curve_point_counts": sorted(point_counts),
                                    "first_training_fractions": sorted(first_fractions),
                                    "final_training_count": next(iter(final_counts)),
                                    "last_training_fraction": next(iter(last_fractions)),
                                },
                            }
                        )
                    errors = [arm["outcome"]["mean_normalized_rmse_auc"] for arm in panel_arms]
                    best, worst = min(errors), max(errors)
                    span = worst - best
                    for arm in panel_arms:
                        error = arm["outcome"]["mean_normalized_rmse_auc"]
                        arm["derived"] = {
                            "native_utility": -error,
                            "panel_normalized_utility": (
                                1.0 if span == 0 else (worst - error) / span
                            ),
                            "panel_normalized_regret": 0.0 if span == 0 else (error - best) / span,
                        }
                    arms.extend(panel_arms)
    return arms


def ingest(results_directory: Path, *, archive: Path | None = None) -> dict:
    if archive is not None:
        if file_hash(archive, "md5") != ARCHIVE_MD5:
            raise ValueError("checksum mismatch for the Zenodo Results.zip archive")
        if file_hash(archive, "sha256") != ARCHIVE_SHA256:
            raise ValueError("SHA-256 mismatch for the Zenodo Results.zip archive")

    results = results_directory / "Results"
    dft_arms = _build_family(
        results / "DFTData" / "al",
        family="computed_dft",
        targets=DFT_TARGETS,
        metrics=DFT_METRICS,
        policies=DFT_POLICIES,
        random_directory="random",
    )
    experimental_arms = _build_family(
        results / "ExperimentalData" / "al",
        family="experimental_thermoelectric",
        targets=EXPERIMENTAL_TARGETS,
        metrics=EXPERIMENTAL_METRICS,
        policies=EXPERIMENTAL_POLICIES,
        random_directory="grow_random",
    )
    arms = sorted(
        dft_arms + experimental_arms,
        key=lambda arm: (arm["panel_id"], arm["environment"]),
    )
    return {
        "artifact": "espinosa_castaneda_2026_diversity_panels_v1",
        "source_id": SOURCE_ID,
        "source_revision": REPOSITORY_REVISION,
        "panel_count": len({arm["panel_id"] for arm in arms}),
        "arm_count": len(arms),
        "primary_outcome": "seed-mean RMSE-AUC over the complete acquisition campaign",
        "normalization": (
            "negative RMSE-AUC, min-max normalized within dataset, target set, "
            "downstream model, and evaluation property"
        ),
        "matched_contract": {
            "fixed_test_fraction": 0.10,
            "initial_acquisition_fraction": 0.01,
            "batch_fraction": 0.01,
            "final_acquisition_fraction": 1.0,
            "campaign_seeds": list(SEEDS),
            "downstream_models": list(MODELS),
        },
        "source_archive": {
            "doi": "10.5281/zenodo.23424148",
            "file": "Results.zip",
            "bytes": 67352831,
            "md5": ARCHIVE_MD5,
            "sha256": ARCHIVE_SHA256,
            "license": "CC-BY-4.0",
        },
        "interpretation_boundary": [
            "Panels use the source's normalized full-campaign RMSE-AUC and never "
            "select a favorable endpoint.",
            "Only policy families with five released seeds for every dataset and "
            "target combination at the corresponding target count enter the bridge.",
            "Targeted and untargeted evaluations are retained separately because "
            "target membership is known before acquisition.",
            "Several panels reuse the same selected dataset across evaluation "
            "properties and downstream models; grouped holdouts therefore operate "
            "at the complete source-dataset level.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_directory", type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(args.results_directory, archive=args.archive)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
