#!/usr/bin/env python3
"""Build the released cross-domain intervention inventory.

The inventory is deliberately read-only. It points back to content-addressed
domain artifacts and preserves their native outcomes, measurements, grouping,
and cost status. It does not create a universal cross-domain utility label.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = Path(__file__).with_name("CORPUS_INVENTORY.json")
DEFAULT_RECORDS_OUTPUT = Path(__file__).with_name("CORPUS_RECORDS.jsonl")

MATERIALS_BRIDGE_FILES = {
    "baghishov_2026_application_specific_mlip": "baghishov_2026_leverage_panels.json",
    "bi_elena_2026_budget_crossover": "bi_elena_2026_budget_crossover_panels.json",
    "dale_2026_active_learning_failure": "dale_2026_active_learning_panels.json",
    "espinosa_castaneda_2026_diversity": "espinosa_castaneda_2026_diversity_panels.json",
    "haenseroth_2026_generators": "haenseroth_2026_generator_panels.json",
    "haenseroth_dressler_2026_data_efficiency": (
        "haenseroth_dressler_2026_trajectory_stride_panels.json"
    ),
    "kim_2026_density_diversity": "kim_2026_density_diversity_panels.json",
    "kulichenko_2023_udd": "kulichenko_2023_udd_cross_test_panels.json",
    "li_2023_redundancy": "li_2023_active_learning_panels.json",
    "liu_2026_heterogeneous_uq": "liu_2026_tungsten_label_panels.json",
    "qi_2024_direct_sampling": "qi_2024_direct_panels.json",
    "varga_umbrich_2026_force_aware_ntk": "varga_umbrich_2026_force_ntk_panels.json",
    "wang_2026_dataset_aware_entropy": "wang_2026_entropy_panels.json",
    "wong_yang_2026_umlip_bias": "wong_yang_2026_umlip_bias_panels.json",
    "zaverkin_2024_uncertainty_biased_md": ("zaverkin_2024_uncertainty_biased_md_panels.json"),
    "zhang_2023_etal": "zhang_2023_etal_panels.json",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def artifact(path: Path) -> dict[str, Any]:
    media_types = {
        ".csv": "text/csv",
        ".json": "application/json",
        ".md": "text/markdown",
    }
    return {
        "path": relative(path),
        "sha256": digest(path),
        "bytes": path.stat().st_size,
        "media_type": media_types[path.suffix],
    }


def record_id(*parts: object) -> str:
    return ":".join(str(part).replace(":", "_") for part in parts)


def candidate_label(arm: dict[str, Any], index: int) -> str:
    for key in (
        "environment",
        "sampling_method",
        "generator",
        "acquisition_policy",
        "method",
        "strategy",
        "selector",
        "training_regime",
        "candidate_id",
        "id",
    ):
        value = arm.get(key)
        if value is not None:
            return str(value)
    return f"source-record-{index}"


class Inventory:
    def __init__(self) -> None:
        self.sources: list[dict[str, Any]] = []
        self.records: list[dict[str, Any]] = []
        self.programs_without_labels: list[dict[str, Any]] = []

    def add_source(
        self,
        *,
        source_id: str,
        domain: str,
        study_id: str,
        files: list[Path],
        evidence_level: str,
        chronology: str,
        cost_status: str,
        notes: list[str],
    ) -> None:
        self.sources.append(
            {
                "source_id": source_id,
                "domain": domain,
                "study_id": study_id,
                "evidence_level": evidence_level,
                "chronology": chronology,
                "cost_status": cost_status,
                "artifacts": [artifact(path) for path in files],
                "notes": notes,
            }
        )

    def add_record(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    def build(self) -> dict[str, Any]:
        ids = [row["record_id"] for row in self.records]
        if len(ids) != len(set(ids)):
            duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
            raise ValueError(f"duplicate record IDs: {duplicates[:5]}")
        source_ids = {source["source_id"] for source in self.sources}
        missing = sorted({row["source_id"] for row in self.records} - source_ids)
        if missing:
            raise ValueError(f"records reference missing sources: {missing}")
        for row in self.records:
            if row["outcome"]["value"] is None:
                raise ValueError(f"missing outcome for {row['record_id']}")
            if not row["panel_id"] or not row["candidate_id"]:
                raise ValueError(f"missing panel or candidate identity for {row['record_id']}")

        by_domain = Counter(row["domain"] for row in self.records)
        by_level = Counter(row["evidence_level"] for row in self.records)
        panels = {(row["source_id"], row["panel_id"]) for row in self.records}
        return {
            "artifact": "anarres_cross_domain_intervention_inventory_v1",
            "status": "released-record inventory; no trained cross-domain surrogate",
            "independent_unit": (
                "one independently trained intervention when seed-level runs are released; "
                "otherwise one explicitly marked published candidate-arm aggregate"
            ),
            "split_rule": (
                "keep every seed, checkpoint, target, and evaluation derived from one "
                "candidate lineage in the same split; primary transfer tests hold out "
                "complete studies or domains"
            ),
            "outcome_rule": (
                "retain native outcomes and direction; compare candidates only within their "
                "declared panel; do not fit a pooled universal utility value"
            ),
            "summary": {
                "sources": len(self.sources),
                "records": len(self.records),
                "panels": len(panels),
                "records_by_domain": dict(sorted(by_domain.items())),
                "records_by_evidence_level": dict(sorted(by_level.items())),
                "programs_without_released_labels": len(self.programs_without_labels),
            },
            "sources": sorted(self.sources, key=lambda row: row["source_id"]),
            "records": sorted(self.records, key=lambda row: row["record_id"]),
            "programs_without_released_labels": sorted(
                self.programs_without_labels, key=lambda row: row["program_id"]
            ),
        }


def add_mathematics(inventory: Inventory) -> None:
    base = ROOT / "experiments/mathematics/environment-utility/results"
    curve_files = [
        base / "g1/1p7b_4b_curves.csv",
        base / "g1/8b_curves.csv",
        base / "g1/14b_curves.csv",
    ]
    cost_files = [
        base / "mechanism/1p7b_4b_training_summary.csv",
        base / "mechanism/8b_training_summary.csv",
        base / "mechanism/14b_training_summary.csv",
    ]
    measurement_file = base / "mechanism/prerl_rho_h.csv"
    source_id = "mathematics_environment_utility"
    inventory.add_source(
        source_id=source_id,
        domain="mathematics",
        study_id="four_scale_environment_utility",
        files=curve_files + cost_files + [measurement_file],
        evidence_level="seed_level_intervention",
        chronology="prospective at 8B and 14B; retrospective at earlier scales",
        cost_status="generated-token cost released for every intervention",
        notes=[
            "The endpoint is step 128; intermediate checkpoints remain nested curve data.",
            "Warm-start performance is reconstructed from released mean outcome and delta.",
        ],
    )
    measurements = {
        (row["scale"].removesuffix("b"), row["cell"]): row for row in read_csv(measurement_file)
    }
    costs: dict[tuple[str, str, int], dict[str, str]] = {}
    for path in cost_files:
        for row in read_csv(path):
            costs[(row["scale"], row["cell"], int(row["seed"]))] = row
    seeds = (9001, 9002)
    for path in curve_files:
        for index, row in enumerate(read_csv(path)):
            if int(row["step"]) != 128:
                continue
            values = [float(value) for value in ast.literal_eval(row["seed_values"])]
            warm_start = float(row["mean_pass_at_1"]) - float(row["delta_from_pi0"])
            scale = row["scale"]
            measurement = measurements[(scale.removesuffix("b"), row["cell"])]
            for seed, outcome in zip(seeds, values, strict=True):
                cost = costs[(scale, row["cell"], seed)]
                inventory.add_record(
                    {
                        "record_id": record_id(source_id, scale, row["cell"], seed),
                        "source_id": source_id,
                        "domain": "mathematics",
                        "study_id": "four_scale_environment_utility",
                        "panel_id": f"{scale}:fixed_trainer",
                        "candidate_id": row["cell"],
                        "training_run_id": cost["run"],
                        "seed": seed,
                        "evidence_level": "seed_level_intervention",
                        "record_pointer": {"artifact": relative(path), "csv_row": index + 2},
                        "prediction_time": {
                            "scale": scale,
                            "starting_success_rate": float(measurement["success_rate"]),
                            "mixed_group_rate": float(measurement["mixed_group_rate"]),
                            "admission_rate": float(measurement["admission_rate"]),
                            "mean_generated_tokens": float(measurement["mean_generated_tokens"]),
                            "rho_per_million_generated_tokens": float(
                                measurement["rho_per_million_generated_tokens"]
                            ),
                            "effective_prompt_coverage": float(
                                measurement["H_effective_prompt_coverage"]
                            ),
                        },
                        "outcome": {
                            "name": "heldout_pass_at_1",
                            "value": outcome,
                            "higher_is_better": True,
                            "utility_from_warm_start": outcome - warm_start,
                            "warm_start": warm_start,
                        },
                        "cost": {
                            "generated_action_tokens": int(
                                float(cost["cumulative_generated_action_tokens"])
                            ),
                            "admitted_tokens": int(float(cost["cumulative_admitted_tokens"])),
                            "status": "released",
                        },
                        "grouping": {"lineage": f"{scale}:{row['cell']}:{seed}", "scale": scale},
                    }
                )


def add_simple_seed_panel(
    inventory: Inventory,
    *,
    source_id: str,
    domain: str,
    study_id: str,
    panel_id: str,
    path: Path,
    records: list[tuple[str, int, float]],
    outcome_name: str,
    higher_is_better: bool,
    prediction_time: dict[str, Any],
    chronology: str,
    notes: list[str],
    extra_files: list[Path] | None = None,
    prediction_time_by_candidate: dict[str, dict[str, Any]] | None = None,
) -> None:
    inventory.add_source(
        source_id=source_id,
        domain=domain,
        study_id=study_id,
        files=[path, *(extra_files or [])],
        evidence_level="seed_level_intervention",
        chronology=chronology,
        cost_status="study-level contract released; per-run compute not always itemized",
        notes=notes,
    )
    for candidate, seed, value in records:
        inventory.add_record(
            {
                "record_id": record_id(source_id, candidate, seed),
                "source_id": source_id,
                "domain": domain,
                "study_id": study_id,
                "panel_id": panel_id,
                "candidate_id": candidate,
                "training_run_id": f"{candidate}:seed-{seed}",
                "seed": seed,
                "evidence_level": "seed_level_intervention",
                "record_pointer": {
                    "artifact": relative(path),
                    "candidate": candidate,
                    "seed": seed,
                },
                "prediction_time": {
                    **prediction_time,
                    **(prediction_time_by_candidate or {}).get(candidate, {}),
                },
                "outcome": {
                    "name": outcome_name,
                    "value": value,
                    "higher_is_better": higher_is_better,
                },
                "cost": {"status": "study_contract_only"},
                "grouping": {"lineage": f"{candidate}:{seed}", "panel": panel_id},
            }
        )


def add_robotics(inventory: Inventory) -> None:
    pusht = ROOT / "experiments/robotics/environment-selection/prospective-pusht/data/outcomes.json"
    payload = read_json(pusht)
    add_simple_seed_panel(
        inventory,
        source_id="robotics_pusht_prospective",
        domain="robotics",
        study_id="prospective_pusht",
        panel_id="pusht:matched_52_episode_environments",
        path=pusht,
        records=[
            (row["arm"], int(row["seed"]), float(row["success_percent"]))
            for row in payload["records"]
        ],
        outcome_name="closed_loop_success_percent",
        higher_is_better=True,
        prediction_time={
            "frozen_inputs": payload["frozen_inputs"],
            "contract": payload["contract"],
        },
        chronology="candidate set and decision frozen before outcomes",
        notes=["Nine independent policy-training runs; evaluation episodes remain nested."],
    )

    can = (
        ROOT / "experiments/robotics/environment-selection/prospective-cupid-can-v141/RESULTS.json"
    )
    payload = read_json(can)
    can_measurements = can.with_name("PROFILE_MEASUREMENTS.json")
    can_profile = read_json(can_measurements)
    can_records = [
        (candidate, int(seed), float(value))
        for candidate, seeds in payload["success_rate_by_arm_and_seed"].items()
        for seed, value in seeds.items()
    ]
    add_simple_seed_panel(
        inventory,
        source_id="robotics_can_v141_prospective",
        domain="robotics",
        study_id="prospective_cupid_can_v141",
        panel_id="can_v141:five_candidate_environments",
        path=can,
        records=can_records,
        outcome_name="closed_loop_success_rate",
        higher_is_better=True,
        prediction_time={"frozen_prediction": payload["frozen_prediction"]},
        chronology="prospective candidate panel scored after frozen prediction",
        notes=[
            "Twenty-five independent policy-training runs across five candidates and five seeds."
        ],
        extra_files=[can_measurements, can.with_name("CANDIDATES.json")],
        prediction_time_by_candidate={
            candidate: {"candidate_measurement": measurement}
            for candidate, measurement in can_profile["candidates"].items()
        },
    )

    square = (
        ROOT
        / "experiments/robotics/environment-selection/prospective-square-regression-v1/RESULTS.json"
    )
    payload = read_json(square)
    square_probe = square.with_name("PROBE_MEASUREMENTS.json")
    square_seeds = (3101, 3102, 3103)
    square_records = [
        (candidate, seed, float(value))
        for candidate, values in payload["arm_seed_success_rates"].items()
        for seed, value in zip(square_seeds, values, strict=True)
    ]
    add_simple_seed_panel(
        inventory,
        source_id="robotics_square_regression_prospective",
        domain="robotics",
        study_id=payload["study_id"],
        panel_id="square:regression_aware_candidate_panel",
        path=square,
        records=square_records,
        outcome_name="closed_loop_success_rate",
        higher_is_better=True,
        prediction_time={
            "point_prediction": payload["point_prediction"],
            "inputs": payload["inputs"],
        },
        chronology="candidate outcomes opened only after the prospective freeze",
        notes=["Eighteen independent policy-training runs; regression diagnostics remain nested."],
        extra_files=[square_probe, square.with_name("CANDIDATES.json")],
    )


def add_legal(inventory: Inventory) -> None:
    path = ROOT / "experiments/legal/environment-selection/data/outcomes.json"
    payload = read_json(path)
    selector_path = path.with_name("selector-freeze.json")
    selector = read_json(selector_path)
    prediction_by_candidate = {
        "frozen_policy_response_allocation": {
            "allocation_weights": selector["weights"],
            "selection_rule": selector["rule"],
        },
        **{
            candidate: {"allocation_weights": weights}
            for candidate, weights in selector["comparators"].items()
        },
    }
    add_simple_seed_panel(
        inventory,
        source_id="legal_syllogym_prospective",
        domain="legal",
        study_id="prospective_syllogym_environment_selection",
        panel_id="syllogym:three_training_environments",
        path=path,
        records=[
            (row["arm"], int(row["seed"]), float(row["completion_percent"]))
            for row in payload["records"]
        ],
        outcome_name="equal_task_macro_all_turn_completion_percent",
        higher_is_better=True,
        prediction_time={"contract": payload["contract"]},
        chronology="frozen candidate decision scored prospectively",
        notes=[
            "Nine independent training runs; task-family guardrails remain nested outcomes.",
            "The separate LAB study has one intervention and is not a candidate panel.",
        ],
        extra_files=[
            path.with_name("measurement-release.json"),
            path.with_name("pretraining-task-measurements.json"),
            selector_path,
            path.with_name("frozen-decision.json"),
        ],
        prediction_time_by_candidate=prediction_by_candidate,
    )


def add_materials_prospective(inventory: Inventory) -> None:
    path = (
        ROOT
        / "experiments/ai-for-science/materials-science"
        / "mlip-phonon-environment-selection/PROSPECTIVE_OUTCOMES.json"
    )
    payload = read_json(path)
    panel_path = path.with_name("FINAL_COST_MATCHED_PANEL.json")
    panel = read_json(panel_path)
    candidate_measurements = {
        candidate["candidate_id"]: {
            key: value for key, value in candidate.items() if key != "record_indices"
        }
        for candidate in panel["candidates"]
    }
    final_rows = [row for row in payload["seed_level_curves"] if int(row["pass"]) == 4]
    source_id = "materials_mlip_phonon_prospective"
    inventory.add_source(
        source_id=source_id,
        domain="materials_science",
        study_id="mlip_phonon_environment_selection",
        files=[
            path,
            panel_path,
            path.with_name("FULL_MEASUREMENT_VALIDATION.json"),
            path.with_name("DECISION_AND_REGRESSION_PROTOCOL.json"),
        ],
        evidence_level="seed_level_intervention",
        chronology="four-candidate prospective panel frozen before outcomes",
        cost_status="matched training contract released; per-run wall time not itemized here",
        notes=[
            "Pass-four outcome is the endpoint; earlier passes remain nested learning-curve data."
        ],
    )
    for row in final_rows:
        candidate = row["candidate_id"]
        seed = int(row["seed"])
        inventory.add_record(
            {
                "record_id": record_id(source_id, candidate, seed),
                "source_id": source_id,
                "domain": "materials_science",
                "study_id": "mlip_phonon_environment_selection",
                "panel_id": "mlip_phonon:four_prospective_candidates",
                "candidate_id": candidate,
                "training_run_id": row["model_sha256"],
                "seed": seed,
                "evidence_level": "seed_level_intervention",
                "record_pointer": {
                    "artifact": relative(path),
                    "candidate": candidate,
                    "seed": seed,
                    "pass": 4,
                },
                "prediction_time": {
                    "candidate_id": candidate,
                    "inputs": payload["inputs"],
                    "candidate_measurement": candidate_measurements[candidate],
                },
                "outcome": {
                    "name": "mean_frequency_mae_thz",
                    "value": float(row["mean_frequency_mae_thz"]),
                    "higher_is_better": False,
                    "utility_thz": float(row["utility_thz"]),
                    "stability_accuracy": float(row["stability_accuracy"]),
                },
                "cost": {"status": "matched_contract_only"},
                "grouping": {"lineage": f"{candidate}:{seed}", "curve_passes": 4},
            }
        )


def add_materials_bridge(inventory: Inventory) -> None:
    base = ROOT / "experiments/ai-for-science/materials-science/retrospective-bridge"
    for study_id, filename in MATERIALS_BRIDGE_FILES.items():
        path = base / "data" / filename
        payload = read_json(path)
        source_id = f"materials_bridge_{study_id}"
        inventory.add_source(
            source_id=source_id,
            domain="materials_science",
            study_id=study_id,
            files=[path],
            evidence_level="published_candidate_arm_aggregate",
            chronology="retrospective public study",
            cost_status="native budget fields retained when released; missing otherwise",
            notes=[
                "This is a publication-derived candidate arm, not automatically a seed-level run.",
                "Comparisons are valid only within the released matched panel.",
            ],
        )
        for index, arm in enumerate(payload["arms"]):
            panel = str(arm["panel_id"])
            candidate = candidate_label(arm, index)
            derived = arm["derived"]
            measurements = arm.get("pre_outcome_measurements", arm.get("method_coordinates", {}))
            if "native_utility" in derived:
                outcome_name = "native_utility"
                outcome_value = float(derived["native_utility"])
                normalized_utility = float(derived["panel_normalized_utility"])
            else:
                outcome_name = "panel_normalized_joint_utility"
                outcome_value = float(derived["panel_normalized_joint_utility"])
                normalized_utility = outcome_value
            inventory.add_record(
                {
                    "record_id": record_id(source_id, index),
                    "source_id": source_id,
                    "domain": "materials_science",
                    "study_id": study_id,
                    "panel_id": panel,
                    "candidate_id": candidate,
                    "training_run_id": None,
                    "seed": None,
                    "evidence_level": "published_candidate_arm_aggregate",
                    "record_pointer": {
                        "artifact": relative(path),
                        "json_pointer": f"/arms/{index}",
                    },
                    "prediction_time": measurements,
                    "outcome": {
                        "name": outcome_name,
                        "value": outcome_value,
                        "higher_is_better": True,
                        "panel_normalized_utility": normalized_utility,
                        "panel_normalized_regret": (
                            None
                            if "panel_normalized_regret" not in derived
                            else float(derived["panel_normalized_regret"])
                        ),
                    },
                    "cost": {"status": "native_fields_only"},
                    "grouping": {"lineage": f"{study_id}:{panel}:{candidate}", "study": study_id},
                }
            )


def add_finance(inventory: Inventory) -> None:
    base = ROOT / "experiments/finance/retrospective-post-training/data"
    curated_path = base / "panels.json"
    curated = read_json(curated_path)
    feature_names = curated["feature_names"]
    source_id = "finance_curated_retrospective_panels"
    inventory.add_source(
        source_id=source_id,
        domain="finance",
        study_id="retrospective_post_training_curated",
        files=[curated_path],
        evidence_level="published_candidate_arm_aggregate",
        chronology="retrospective public studies",
        cost_status="training cost incomplete; treatment descriptors retained",
        notes=["Controls and trained candidates retain their explicit panel roles."],
    )
    for panel_index, panel in enumerate(curated["panels"]):
        for arm_index, arm in enumerate(panel["arms"]):
            candidate = arm["id"]
            inventory.add_record(
                {
                    "record_id": record_id(source_id, panel["panel_id"], candidate),
                    "source_id": source_id,
                    "domain": "finance",
                    "study_id": panel["study_id"],
                    "panel_id": panel["panel_id"],
                    "candidate_id": candidate,
                    "training_run_id": None,
                    "seed": None,
                    "evidence_level": "published_candidate_arm_aggregate",
                    "record_pointer": {
                        "artifact": relative(curated_path),
                        "json_pointer": f"/panels/{panel_index}/arms/{arm_index}",
                    },
                    "prediction_time": dict(zip(feature_names, arm["features"], strict=True)),
                    "outcome": {
                        "name": panel["metric"],
                        "value": float(arm["score"]),
                        "higher_is_better": True,
                    },
                    "cost": {"status": "missing"},
                    "grouping": {
                        "lineage": f"{panel['study_id']}:{panel['panel_id']}:{candidate}",
                        "role": "control" if candidate == panel["baseline"] else "candidate",
                    },
                }
            )

    recovered_path = base / "recovered_panels.json"
    recovered = read_json(recovered_path)
    source_id = "finance_recovered_retrospective_panels"
    inventory.add_source(
        source_id=source_id,
        domain="finance",
        study_id="retrospective_post_training_recovered",
        files=[recovered_path],
        evidence_level="published_candidate_arm_aggregate",
        chronology="retrospective public studies",
        cost_status="sample counts retained where released; compute cost incomplete",
        notes=["Every record retains source identity for complete-source holdout."],
    )
    for panel_index, panel in enumerate(recovered["panels"]):
        for arm_index, arm in enumerate(panel["arms"]):
            candidate = arm["id"]
            inventory.add_record(
                {
                    "record_id": record_id(source_id, panel["panel_id"], candidate),
                    "source_id": source_id,
                    "domain": "finance",
                    "study_id": panel["source_id"],
                    "panel_id": panel["panel_id"],
                    "candidate_id": candidate,
                    "training_run_id": None,
                    "seed": None,
                    "evidence_level": "published_candidate_arm_aggregate",
                    "record_pointer": {
                        "artifact": relative(recovered_path),
                        "json_pointer": f"/panels/{panel_index}/arms/{arm_index}",
                    },
                    "prediction_time": arm.get("treatment", {}),
                    "outcome": {
                        "name": panel["metric"],
                        "value": float(arm["score"]),
                        "higher_is_better": bool(panel["higher_is_better"]),
                    },
                    "cost": {
                        "status": "partial"
                        if "sample_count" in arm.get("treatment", {})
                        else "missing",
                        "sample_count": arm.get("treatment", {}).get("sample_count"),
                    },
                    "grouping": {
                        "lineage": f"{panel['source_id']}:{panel['panel_id']}:{candidate}",
                        "source": panel["source_id"],
                    },
                }
            )


def add_unlabeled_programs(inventory: Inventory) -> None:
    programs = [
        (
            "agentic_customer_support",
            "agentic_systems",
            "experiments/agentic/customer-support-environment-utility/README.md",
            "prospective workflow exists; candidate-training outcomes are not released",
        ),
        (
            "cyber_formal_verification",
            "cyber",
            "experiments/cyber/formal-verification/README.md",
            "qualification evidence exists; no released multi-candidate training comparison",
        ),
        (
            "cyber_vulnerability_exploitation",
            "cyber",
            "experiments/cyber/README.md",
            "starting-policy measurement evidence exists; no released intervention panel",
        ),
        (
            "legal_lab_learning_dynamics",
            "legal",
            "experiments/legal/lab-learning-dynamics/README.md",
            "one intervention with checkpoint regressions; not a candidate-environment panel",
        ),
        (
            "molecular_design_acquisition",
            "molecular_design",
            "experiments/ai-for-science/molecular-design/README.md",
            "released acquisition outcomes operate at a different decision level",
        ),
    ]
    for program_id, domain, path_text, reason in programs:
        path = ROOT / path_text
        inventory.programs_without_labels.append(
            {
                "program_id": program_id,
                "domain": domain,
                "status": "not_eligible_for_intervention_supervision",
                "reason": reason,
                "artifact": artifact(path),
            }
        )


def build_inventory() -> dict[str, Any]:
    inventory = Inventory()
    add_mathematics(inventory)
    add_robotics(inventory)
    add_legal(inventory)
    add_materials_prospective(inventory)
    add_materials_bridge(inventory)
    add_finance(inventory)
    add_unlabeled_programs(inventory)
    return inventory.build()


def render_inventory(inventory: dict[str, Any], records_filename: str) -> tuple[str, str]:
    records = inventory["records"]
    records_rendered = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in records
    )
    manifest = {key: value for key, value in inventory.items() if key != "records"}
    manifest["records_artifact"] = {
        "filename": records_filename,
        "sha256": hashlib.sha256(records_rendered.encode()).hexdigest(),
        "bytes": len(records_rendered.encode()),
        "media_type": "application/x-ndjson",
        "records": len(records),
    }
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n", records_rendered


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--records-output", type=Path, default=DEFAULT_RECORDS_OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the output differs")
    args = parser.parse_args()
    rendered, records_rendered = render_inventory(build_inventory(), args.records_output.name)
    if args.check:
        if (
            not args.output.exists()
            or args.output.read_text() != rendered
            or not args.records_output.exists()
            or args.records_output.read_text() != records_rendered
        ):
            raise SystemExit(f"stale cross-domain inventory: {args.output}")
        return
    args.output.write_text(rendered)
    args.records_output.write_text(records_rendered)


if __name__ == "__main__":
    main()
