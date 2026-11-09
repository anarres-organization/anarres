#!/usr/bin/env python3
"""Evaluate compact predictors under source-specific grouped holdouts."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

FILES = {
    "li_2023_redundancy": "li_2023_active_learning_panels.json",
    "haenseroth_2026_generators": "haenseroth_2026_generator_panels.json",
    "kulichenko_2023_udd": "kulichenko_2023_udd_cross_test_panels.json",
    "dale_2026_active_learning_failure": "dale_2026_active_learning_panels.json",
    "bi_elena_2026_budget_crossover": "bi_elena_2026_budget_crossover_panels.json",
    "wong_yang_2026_umlip_bias": "wong_yang_2026_umlip_bias_panels.json",
    "baghishov_2026_application_specific_mlip": "baghishov_2026_leverage_panels.json",
    "qi_2024_direct_sampling": "qi_2024_direct_panels.json",
    "zaverkin_2024_uncertainty_biased_md": "zaverkin_2024_uncertainty_biased_md_panels.json",
    "zhang_2023_etal": "zhang_2023_etal_panels.json",
    "espinosa_castaneda_2026_diversity": "espinosa_castaneda_2026_diversity_panels.json",
    "wang_2026_dataset_aware_entropy": "wang_2026_entropy_panels.json",
    "varga_umbrich_2026_pretrained_acquisition": "varga_umbrich_2026_transfer_panels.json",
    "kim_2026_density_diversity": "kim_2026_density_diversity_panels.json",
    "liu_2026_heterogeneous_uq": "liu_2026_tungsten_label_panels.json",
    "haenseroth_dressler_2026_data_efficiency": (
        "haenseroth_dressler_2026_trajectory_stride_panels.json"
    ),
}
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)


def records(source: str, payload: dict) -> list[dict]:
    result = []
    for arm in payload["arms"]:
        if source == "li_2023_redundancy":
            coordinates = arm["method_coordinates"]
            features = [
                coordinates["uses_model_relative_signal"],
                coordinates["uses_committee_disagreement"],
                coordinates["uses_predictive_uncertainty"],
                coordinates["acquisition_model_match"],
            ]
            practical = (
                coordinates["uses_model_relative_signal"]
                + coordinates["uses_committee_disagreement"]
                + (coordinates["acquisition_model_match"] or 0)
            )
            group = arm["panel_id"].rsplit(":", 1)[0]
            identity = arm["method"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "haenseroth_2026_generators":
            coordinates = arm["pre_outcome_measurements"]
            error = coordinates["generator_zero_shot_force_mae_eV_per_A"]
            features = [-error]
            practical = -error
            group = arm["material_system"]
            identity = arm["generator"]
            utility = arm["derived"]["panel_normalized_joint_utility"]
        elif source == "kulichenko_2023_udd":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_uncertainty_bias"],
                coordinates["high_energy_region_count"],
                -coordinates["temperature_gap_to_target_K"],
                coordinates["uncertainty_bias_matches_target"],
                -coordinates["high_energy_count_gap_to_target"],
            ]
            practical = (
                -coordinates["temperature_gap_to_target_K"] / 1000
                - coordinates["high_energy_count_gap_to_target"] / 400
                + coordinates["uncertainty_bias_matches_target"]
            )
            group = arm["target_environment"]
            identity = arm["training_environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "dale_2026_active_learning_failure":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["selects_by_uncertainty"],
                coordinates["ensemble_source"],
                coordinates["loss_landscape_source"],
                coordinates["calibration_complexity"],
            ]
            # The source's own scientific question is whether uncertainty-based
            # selection improves on random sampling. No calibration ordering is
            # assumed in this practical rule.
            practical = coordinates["selects_by_uncertainty"]
            group = arm["panel_id"].rsplit(":", 1)[0]
            identity = arm["acquisition_method"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "bi_elena_2026_budget_crossover":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_structural_coverage"],
                coordinates["uses_learned_embedding"],
                coordinates["uses_response_disagreement"],
                coordinates["requires_full_data_reference"],
                coordinates["retained_budget_fraction"],
                coordinates["response_budget_interaction"],
            ]
            # A deployable coverage rule prefers structural coverage while
            # excluding selectors that require a full-data reference model.
            practical = (
                coordinates["uses_structural_coverage"]
                - coordinates["requires_full_data_reference"]
            )
            group = arm["dataset"]
            identity = arm["selector"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "wong_yang_2026_umlip_bias":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                -coordinates["starting_energy_mae_meV_per_atom"],
                -coordinates["starting_energy_rmse_meV_per_atom"],
                coordinates["effective_configuration_coverage_energy_error"],
                coordinates["configuration_count"],
            ]
            practical = -coordinates["starting_energy_mae_meV_per_atom"]
            group = arm["panel_id"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "baghishov_2026_application_specific_mlip":
            coordinates = arm["pre_outcome_measurements"]
            target_match = (
                coordinates["uses_energy_leverage"]
                if arm["endpoint"] == "testing_energy_rmse"
                else coordinates["uses_force_block_leverage"]
            )
            features = [
                coordinates["uses_descriptor_coverage"],
                coordinates["uses_energy_leverage"],
                coordinates["uses_force_block_leverage"],
                target_match,
                coordinates["training_pool_fraction"],
            ]
            practical = target_match
            group = arm["training_configuration_count"]
            identity = arm["sampling_method"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "qi_2024_direct_sampling":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["structural_coverage"],
                coordinates["target_distribution_match"],
                coordinates["training_configuration_count"],
            ]
            practical = coordinates["target_distribution_match"]
            group = arm["evaluation_distribution"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "zaverkin_2024_uncertainty_biased_md":
            coordinates = arm["pre_outcome_measurements"]
            coverage = coordinates["structural_coverage"]
            features = [
                coordinates["uses_uncertainty_selection"],
                coordinates["uses_uncertainty_bias"],
                coordinates["adaptive_acquisition"],
                -coordinates["temperature_gap_to_test_K"],
                coverage,
            ]
            practical = (
                coverage
                if coverage is not None
                else coordinates["uses_uncertainty_selection"]
                + coordinates["uses_uncertainty_bias"]
                - coordinates["temperature_gap_to_test_K"] / 600.0
            )
            if arm["system"] == "alanine_dipeptide":
                group = "alanine_dipeptide"
            else:
                group = f"mil53_{coordinates['generation_temperature_K']}K"
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "zhang_2023_etal":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_entropy_targeting"],
                coordinates["targets_underrepresented_structure_space"],
                coordinates["adaptive_acquisition"],
                coordinates["final_training_count"],
            ]
            practical = coordinates["targets_underrepresented_structure_space"]
            group = arm["target"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "espinosa_castaneda_2026_diversity":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_model_disagreement"],
                coordinates["uses_outcome_disagreement_diversity"],
                coordinates["uses_feature_space_diversity"],
                coordinates["adaptive_acquisition"],
                coordinates["targets_evaluation_property"],
                coordinates["target_property_count"],
                coordinates["initial_training_count"],
            ]
            practical = (
                coordinates["targets_evaluation_property"]
                + coordinates["uses_outcome_disagreement_diversity"]
                + coordinates["uses_feature_space_diversity"]
            )
            group = arm["dataset"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "wang_2026_dataset_aware_entropy":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_dataset_entropy"],
                coordinates["uses_structural_coverage_selection"],
                coordinates["targets_underrepresented_structure_space"],
                coordinates["target_distribution_match"],
                coordinates["adaptive_acquisition"],
                coordinates["training_configuration_count"],
            ]
            # Broad structural coverage and evaluation-distribution match are
            # both known before fitting the downstream potential. On the
            # independent equilibrium/thermal test they offset, yielding an
            # honest tie rather than choosing a direction from the outcomes.
            practical = (
                coordinates["uses_structural_coverage_selection"]
                + coordinates["target_distribution_match"]
            )
            group = arm["material_system"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "varga_umbrich_2026_pretrained_acquisition":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["uses_pretrained_representation_kernel"],
                coordinates["uses_model_relative_signal"],
                coordinates["uses_lcmd_structural_coverage"],
                coordinates["uses_pointwise_committee_disagreement"],
                coordinates["acquisition_signal_matches_energy_endpoint"],
                -coordinates["forward_passes_per_candidate"],
                -coordinates["backward_passes_per_candidate"],
                -coordinates["models_maintained"],
            ]
            # This outcome-blind rule tests the paper's central proposal:
            # pretrained representation kernels coupled to LCMD coverage.
            practical = coordinates["uses_pretrained_representation_kernel"]
            group = arm["dataset"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "kim_2026_density_diversity":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["training_density_span_g_cm3"],
                coordinates["training_temperature_span_K"],
                -coordinates["closest_density_gap_g_cm3"],
                -coordinates["closest_temperature_gap_K"],
                coordinates["target_density_inside_training_range"],
                coordinates["target_temperature_inside_training_range"],
            ]
            # This outcome-blind rule represents the paper's central design
            # principle: prefer broad density support that reaches the target.
            practical = (
                coordinates["training_density_span_g_cm3"]
                - coordinates["closest_density_gap_g_cm3"]
            )
            group = arm["evaluation_temperature_K"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "liu_2026_heterogeneous_uq":
            coordinates = arm["pre_outcome_measurements"]
            features = [
                coordinates["dft_atomic_environment_fraction"],
                coordinates["umlip_atomic_environment_fraction"],
                coordinates["uses_model_relative_uncertainty_partition"],
                coordinates["matches_independently_validated_uc1_threshold"],
            ]
            # The study validates U_c=1 on separate public DFT datasets before
            # applying that threshold to the tungsten downstream comparison.
            practical = coordinates["matches_independently_validated_uc1_threshold"]
            group = arm["endpoint"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        elif source == "haenseroth_dressler_2026_data_efficiency":
            coordinates = arm["pre_outcome_measurements"]
            span = np.log10(coordinates["relative_trajectory_span"])
            count = np.log10(coordinates["training_configuration_count"])
            pretrained = coordinates["uses_pretrained_initialization"]
            force_endpoint = float(arm["endpoint"] == "force_mae_eV_per_A")
            features = [
                span,
                count,
                pretrained,
                force_endpoint,
                span * count,
                span * pretrained,
                span * force_endpoint,
            ]
            # At fixed DFT-label and training budgets, the wider trajectory
            # span is the source's direct coverage intervention. Generating
            # that parent trajectory can cost more and is reported separately.
            practical = span
            group = arm["material_system"]
            identity = arm["environment"]
            utility = arm["derived"]["panel_normalized_utility"]
        else:
            raise KeyError(source)
        result.append(
            {
                "source": source,
                "panel": arm["panel_id"],
                "group": group,
                "identity": identity,
                "features": features,
                "practical": practical,
                "utility": utility,
            }
        )
    return result


def design(train: list[dict], test: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    train_x = np.asarray(
        [[np.nan if value is None else float(value) for value in row["features"]] for row in train]
    )
    test_x = np.asarray(
        [[np.nan if value is None else float(value) for value in row["features"]] for row in test]
    )
    missing_train = np.isnan(train_x).astype(float)
    missing_test = np.isnan(test_x).astype(float)
    counts = np.sum(~np.isnan(train_x), axis=0)
    means = np.divide(
        np.nansum(train_x, axis=0),
        counts,
        out=np.zeros(train_x.shape[1], dtype=float),
        where=counts > 0,
    )
    train_x = np.where(np.isnan(train_x), means, train_x)
    test_x = np.where(np.isnan(test_x), means, test_x)
    centers = train_x.mean(axis=0)
    scales = train_x.std(axis=0)
    scales = np.where(scales == 0, 1.0, scales)
    train_x = (train_x - centers) / scales
    test_x = (test_x - centers) / scales
    # Missingness columns are retained only when they vary in the training fold.
    varying_missing = missing_train.std(axis=0) > 0
    if np.any(varying_missing):
        train_x = np.column_stack([train_x, missing_train[:, varying_missing]])
        test_x = np.column_stack([test_x, missing_test[:, varying_missing]])
    return train_x, test_x


def ridge_predict(train: list[dict], test: list[dict], alpha: float) -> np.ndarray:
    train_x, test_x = design(train, test)
    y = np.asarray([row["utility"] for row in train], dtype=float)
    x_mean = train_x.mean(axis=0)
    y_mean = y.mean()
    centered = train_x - x_mean
    beta = np.linalg.solve(
        centered.T @ centered + alpha * np.eye(centered.shape[1]),
        centered.T @ (y - y_mean),
    )
    return y_mean + (test_x - x_mean) @ beta


def choose_alpha(train: list[dict]) -> float:
    groups = sorted({row["group"] for row in train})
    if len(groups) < 3:
        return 1.0
    losses = {}
    for alpha in ALPHAS:
        squared = []
        for group in groups:
            inner_train = [row for row in train if row["group"] != group]
            inner_test = [row for row in train if row["group"] == group]
            predictions = ridge_predict(inner_train, inner_test, alpha)
            squared.extend(
                (prediction - row["utility"]) ** 2
                for prediction, row in zip(predictions, inner_test, strict=True)
            )
        losses[alpha] = float(np.mean(squared))
    return min(ALPHAS, key=lambda alpha: (losses[alpha], alpha))


def oof_predictions(rows: list[dict]) -> dict[str, list[float]]:
    predictions = {"uninformed_tie": [], "practical_rule": [], "fixed_identity": [], "ridge": []}
    groups = sorted({row["group"] for row in rows})
    ordered_rows = []
    fold_alphas = []
    for group in groups:
        train = [row for row in rows if row["group"] != group]
        test = [row for row in rows if row["group"] == group]
        ordered_rows.extend(test)
        predictions["uninformed_tie"].extend([0.0] * len(test))
        predictions["practical_rule"].extend(row["practical"] for row in test)

        identity_means: dict[str, list[float]] = defaultdict(list)
        for row in train:
            identity_means[row["identity"]].append(row["utility"])
        means = {key: float(np.mean(values)) for key, values in identity_means.items()}
        best = max(means.values())
        selected = {key for key, value in means.items() if np.isclose(value, best)}
        predictions["fixed_identity"].extend(
            1.0 if row["identity"] in selected else 0.0 for row in test
        )

        alpha = choose_alpha(train)
        fold_alphas.append(alpha)
        predictions["ridge"].extend(ridge_predict(train, test, alpha))
    predictions["rows"] = ordered_rows
    predictions["fold_alphas"] = fold_alphas
    return predictions


def metrics(rows: list[dict], predictions: list[float]) -> dict:
    by_panel: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        by_panel[row["panel"]].append(index)
    pair_credit = []
    regrets = []
    top_credit = []
    for indices in by_panel.values():
        for left_at, left in enumerate(indices):
            for right in indices[left_at + 1 :]:
                observed = rows[left]["utility"] - rows[right]["utility"]
                predicted = predictions[left] - predictions[right]
                if np.isclose(observed, 0) or np.isclose(predicted, 0):
                    pair_credit.append(0.5)
                else:
                    pair_credit.append(float(np.sign(observed) == np.sign(predicted)))
        best_prediction = max(predictions[index] for index in indices)
        selected = [index for index in indices if np.isclose(predictions[index], best_prediction)]
        best_utility = max(rows[index]["utility"] for index in indices)
        selected_utility = float(np.mean([rows[index]["utility"] for index in selected]))
        regrets.append(best_utility - selected_utility)
        top_credit.append(
            float(np.mean([np.isclose(rows[index]["utility"], best_utility) for index in selected]))
        )
    return {
        "pairwise_ordering": float(np.mean(pair_credit)),
        "mean_normalized_regret": float(np.mean(regrets)),
        "top_choice_credit": float(np.mean(top_credit)),
    }


def analyze(data: Path) -> dict:
    source_results = {}
    total_panels = 0
    total_arms = 0
    for source, filename in FILES.items():
        payload = json.loads((data / filename).read_text(encoding="utf-8"))
        rows = records(source, payload)
        result = oof_predictions(rows)
        source_results[source] = {
            "support": {
                "groups": len({row["group"] for row in rows}),
                "panels": len({row["panel"] for row in rows}),
                "arms": len(rows),
            },
            "fold_alphas": result["fold_alphas"],
            "metrics": {
                rule: metrics(result["rows"], values)
                for rule, values in result.items()
                if rule not in {"rows", "fold_alphas"}
            },
        }
        total_panels += source_results[source]["support"]["panels"]
        total_arms += len(rows)
    return {
        "artifact": "materials_source_specific_grouped_holdouts_v1",
        "design": "nested grouped holdout within each source",
        "support": {"sources": len(source_results), "panels": total_panels, "arms": total_arms},
        "sources": source_results,
        "interpretation_boundary": [
            "Outcomes are normalized only within matched decision panels.",
            "Source-specific coordinates are not assumed to share units or coefficients.",
            "Method identities define a negative-control selector and are not ridge features.",
            "These retrospective tests do not replace the sealed prospective phonon study.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = analyze(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["support"]))


if __name__ == "__main__":
    main()
