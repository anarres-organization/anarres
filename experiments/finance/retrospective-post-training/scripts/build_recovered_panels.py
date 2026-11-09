#!/usr/bin/env python3
"""Build the source-audited finance intervention panel recovered from tables."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "recovered_panels.json"


def arm(arm_id: str, score: float, **treatment: object) -> dict:
    return {"id": arm_id, "score": score, "treatment": treatment}


def panel(
    source_id: str,
    panel_id: str,
    evidence: str,
    model: str,
    target: str,
    arms: list[dict],
    *,
    metric: str = "accuracy_percent",
    budget_matched: bool,
) -> dict:
    return {
        "source_id": source_id,
        "panel_id": panel_id,
        "evidence": evidence,
        "model": model,
        "target": target,
        "metric": metric,
        "higher_is_better": True,
        "budget_matched": budget_matched,
        "arms": arms,
    }


def phogat_2024() -> list[dict]:
    models = ["mistral_7b", "orca2_7b", "orca2_13b", "phi3_mini", "phi3_medium"]
    table4_finqa = [
        [76.63, 70.35, 68.78, 64.95],
        [71.57, 63.56, 67.13, 55.01],
        [73.75, 70.53, 70.09, 65.13],
        [73.49, 69.83, 71.14, 68.87],
        [77.59, 74.71, 75.06, 74.80],
    ]
    table4_conv = [
        [36.34, 33.01, 72.20, 76.48],
        [41.09, 32.30, 69.12, 70.30],
        [36.82, 41.81, 72.92, 75.77],
        [44.89, 49.40, 72.20, 76.00],
        [53.44, 51.54, 79.57, 81.94],
    ]
    table5_finqa = [
        [76.63, 70.35, 70.01, 56.06],
        [71.57, 63.56, 67.48, 57.11],
        [73.75, 70.53, 68.70, 63.55],
        [73.49, 69.83, 70.70, 63.81],
        [77.59, 74.71, 72.44, 70.96],
    ]
    table5_tatqa = [
        [84.26, 78.41, 83.98, 88.71],
        [79.38, 72.56, 80.64, 88.57],
        [80.78, 79.94, 85.93, 88.86],
        [81.19, 74.51, 86.07, 90.94],
        [88.30, 85.79, 88.16, 93.03],
    ]

    def qa_arms(
        values: list[float], other_source: str, other_full: int, evaluation_target: str
    ) -> list[dict]:
        def aligned_fraction(finqa_count: int, other_count: int) -> float:
            if evaluation_target == "finqa":
                return finqa_count / (finqa_count + other_count)
            return other_count / (finqa_count + other_count)

        return [
            arm(
                "finqa_full",
                values[0],
                sample_count=5698,
                source="finqa",
                target_fraction=aligned_fraction(5698, 0),
            ),
            arm(
                "finqa_1500",
                values[1],
                sample_count=1500,
                source="finqa",
                target_fraction=aligned_fraction(1500, 0),
            ),
            arm(
                f"finqa1000_{other_source}500",
                values[2],
                sample_count=1500,
                source=f"finqa+{other_source}",
                source_diversity=2,
                target_fraction=aligned_fraction(1000, 500),
            ),
            arm(
                f"{other_source}_full",
                values[3],
                sample_count=other_full,
                source=other_source,
                target_fraction=aligned_fraction(0, other_full),
            ),
        ]

    panels = []
    for i, model in enumerate(models):
        panels.extend(
            [
                panel(
                    "phogat2024_financial_qa",
                    f"phogat_t4_{model}_finqa",
                    "Table 4",
                    model,
                    "finqa",
                    qa_arms(table4_finqa[i], "convfinqa", 2550, "finqa"),
                    budget_matched=False,
                ),
                panel(
                    "phogat2024_financial_qa",
                    f"phogat_t4_{model}_convfinqa",
                    "Table 4",
                    model,
                    "convfinqa",
                    qa_arms(table4_conv[i], "convfinqa", 2550, "convfinqa"),
                    budget_matched=False,
                ),
                panel(
                    "phogat2024_financial_qa",
                    f"phogat_t5_{model}_finqa",
                    "Table 5",
                    model,
                    "finqa",
                    qa_arms(table5_finqa[i], "tatqa", 4878, "finqa"),
                    budget_matched=False,
                ),
                panel(
                    "phogat2024_financial_qa",
                    f"phogat_t5_{model}_tatqa",
                    "Table 5",
                    model,
                    "tatqa",
                    qa_arms(table5_tatqa[i], "tatqa", 4878, "tatqa"),
                    budget_matched=False,
                ),
            ]
        )
    return panels


def harsha_2025() -> list[dict]:
    panels = []
    tables = {
        "finqa": {
            "finqa": {750: (63.99, 69.83), 1500: (64.95, 71.31), 3000: (68.61, 71.49)},
            "tatqa": {750: (82.17, 81.19), 1500: (83.56, 79.66), 3000: (82.31, 81.75)},
        },
        "tatqa": {
            "finqa": {750: (65.47, 64.86), 1500: (65.47, 64.16), 3000: (67.56, 63.46)},
            "tatqa": {750: (85.51, 87.04), 1500: (87.88, 86.09), 3000: (88.02, 88.30)},
        },
    }
    for training_source, targets in tables.items():
        for target, budgets in targets.items():
            for sample_count, (synthetic, real) in budgets.items():
                panels.append(
                    panel(
                        "harsha2025_synthetic_financial_qa",
                        f"harsha_{training_source}_{target}_{sample_count}",
                        "Table 2" if training_source == "finqa" else "Table 3",
                        "phi3_mini",
                        target,
                        [
                            arm(
                                "synthetic",
                                synthetic,
                                sample_count=sample_count,
                                source=training_source,
                                synthetic_fraction=1.0,
                            ),
                            arm(
                                "real",
                                real,
                                sample_count=sample_count,
                                source=training_source,
                                synthetic_fraction=0.0,
                            ),
                        ],
                        budget_matched=True,
                    )
                )

    selection = {
        ("finqa", "finqa"): [66.43, 64.16, 63.99],
        ("finqa", "tatqa"): [83.42, 82.17, 82.17],
        ("tatqa", "finqa"): [63.20, 65.91, 65.47],
        ("tatqa", "tatqa"): [84.67, 85.65, 85.51],
    }
    for (training_source, target), values in selection.items():
        panels.append(
            panel(
                "harsha2025_synthetic_financial_qa",
                f"harsha_distance_{training_source}_{target}",
                "Table 4",
                "phi3_mini",
                target,
                [
                    arm("closest", values[0], sample_count=750, selection="closest_to_real"),
                    arm("farthest", values[1], sample_count=750, selection="farthest_from_real"),
                    arm("random", values[2], sample_count=750, selection="random"),
                ],
                budget_matched=True,
            )
        )

    conv = {
        "phi3_mini": [55.81, 52.96, 62.00, 67.00, 76.00],
        "phi3_medium": [65.58, 64.37, 71.49, 73.81, 81.94],
        "mistral_7b": [52.73, 57.24, 65.32, 65.79, 76.72],
    }
    conv_ids = ["derived", "derived_examples", "direct", "conv_plus_finqa", "real"]
    for model, values in conv.items():
        panels.append(
            panel(
                "harsha2025_synthetic_financial_qa",
                f"harsha_conv_generation_{model}",
                "Table 5",
                model,
                "convfinqa_overall",
                [
                    arm(
                        arm_id,
                        score,
                        source_diversity=2 if arm_id == "conv_plus_finqa" else 1,
                        synthetic_fraction=0.0 if arm_id == "real" else 1.0,
                        generation_method=arm_id,
                    )
                    for arm_id, score in zip(conv_ids, values, strict=True)
                ],
                budget_matched=True,
            )
        )

    panels.append(
        panel(
            "harsha2025_synthetic_financial_qa",
            "harsha_real_fraction_phi3_mini",
            "Table 6",
            "phi3_mini",
            "convfinqa_overall",
            [
                arm("real_10", 69.98, real_fraction=0.10, synthetic_fraction=0.90),
                arm("real_20", 73.07, real_fraction=0.20, synthetic_fraction=0.80),
                arm("real_40", 74.87, real_fraction=0.40, synthetic_fraction=0.60),
                arm("real_100", 76.00, real_fraction=1.00, synthetic_fraction=0.00),
            ],
            budget_matched=True,
        )
    )
    return panels


def fin_prm_2026() -> list[dict]:
    return [
        panel(
            "fin_prm_2026",
            "fin_prm_offline_selection",
            "Table 1",
            "qwen2.5_7b_instruct",
            "cflue",
            [
                arm("none", 45.3, sample_count=0, selection="none"),
                arm("random", 43.8, sample_count=1000, selection="random"),
                arm(
                    "math_prm_7b", 56.5, sample_count=1000, selection="math_prm", selector_scale_b=7
                ),
                arm(
                    "math_prm_72b",
                    57.1,
                    sample_count=1000,
                    selection="math_prm",
                    selector_scale_b=72,
                ),
                arm(
                    "fin_prm",
                    58.2,
                    sample_count=1000,
                    selection="finance_prm",
                    domain_specific=True,
                ),
            ],
            budget_matched=False,
        )
    ]


def fin_sd_2026() -> list[dict]:
    return [
        panel(
            "fin_sd_2026",
            "fin_sd_method_comparison",
            "Table 2",
            "gpt_oss_20b",
            "finance_reasoning_hard",
            [
                arm("base", 69.16, method="none", seeds=5),
                arm("sft", 62.46, method="reference_sft", seeds=3),
                arm("opsd", 70.42, method="full_solution_opsd", seeds=5),
                arm("fin_sd", 72.19, method="localized_self_distillation", seeds=5),
            ],
            budget_matched=False,
        ),
        panel(
            "fin_sd_2026",
            "fin_sd_ablation",
            "Table 5",
            "gpt_oss_20b",
            "finance_reasoning_hard",
            [
                arm("self_rkl", 72.19, hint_writer="self", kl="reverse", rollout_cap=100, seeds=5),
                arm("self_fkl", 70.93, hint_writer="self", kl="forward", rollout_cap=100, seeds=5),
                arm(
                    "teacher120b_fkl",
                    71.26,
                    hint_writer="gpt_oss_120b",
                    kl="forward",
                    rollout_cap=100,
                    seeds=5,
                ),
                arm(
                    "teacher120b_rkl",
                    72.19,
                    hint_writer="gpt_oss_120b",
                    kl="reverse",
                    rollout_cap=100,
                    seeds=5,
                ),
                arm(
                    "long_rollout",
                    71.09,
                    hint_writer="self",
                    kl="reverse",
                    rollout_cap=8192,
                    seeds=5,
                ),
            ],
            budget_matched=False,
        ),
    ]


def shin_kim_2026() -> list[dict]:
    """Recover the finance-trained cells from the complete Table 13 factorial."""
    rows = {
        "exaone3p5_2p4b": [
            [43.37, 40.26, 40.22, 41.19, 41.00],
            [44.83, 38.65, 39.39, 40.45, 40.33],
            [60.75, 55.54, 55.12, 55.74, 55.74],
        ],
        "gemma3_4b": [
            [37.88, 35.49, 35.02, 35.76, 35.41],
            [42.50, 41.20, 38.60, 39.38, 40.05],
            [60.56, 56.84, 56.25, 56.85, 56.44],
        ],
        "llama3p2_3b": [
            [37.30, 36.89, 37.34, 37.21, 37.37],
            [40.00, 37.97, 37.91, 38.35, 37.86],
            [64.91, 62.24, 62.08, 62.22, 62.23],
        ],
        "phi4_mini": [
            [36.94, 36.42, 36.60, 35.94, 36.70],
            [37.45, 34.71, 35.65, 35.13, 36.22],
            [70.42, 66.37, 66.45, 66.41, 66.38],
        ],
        "qwen3p5_4b": [
            [47.13, 49.43, 50.98, 50.31, 51.10],
            [50.61, 52.30, 52.18, 52.82, 52.16],
            [79.28, 74.00, 74.11, 73.91, 73.91],
        ],
        "exaone3p5_7p8b": [
            [45.35, 39.83, 38.40, 38.11, 39.64],
            [51.24, 44.11, 44.74, 44.97, 46.09],
            [67.88, 62.08, 61.95, 62.40, 62.05],
        ],
        "qwen3p5_9b": [
            [58.98, 56.74, 57.40, 57.78, 59.01],
            [61.43, 58.38, 58.81, 59.20, 60.09],
            [83.28, 77.21, 76.84, 77.00, 77.36],
        ],
        "gemma3_27b": [
            [55.01, 51.86, 51.67, 51.87, 51.76],
            [60.91, 59.25, 57.65, 57.62, 57.14],
            [77.88, 74.71, 74.05, 74.34, 74.43],
        ],
        "llama3p3_70b": [
            [57.66, 56.06, 55.97, 55.83, 56.25],
            [61.84, 59.41, 59.54, 58.94, 59.86],
            [83.37, 82.10, 82.03, 81.92, 82.09],
        ],
    }
    targets = ["kmmlu", "kmmlu_finance", "mmlu"]
    condition_ids = ["base", "exp0", "exp1_1", "exp1_2", "exp2"]
    conditions = [
        {"training_stage": "none", "training_domain": "finance", "seeds": 1},
        {
            "training_stage": "sft",
            "training_domain": "finance",
            "transcript_refinement": False,
            "qa_refinement": False,
            "seeds": 2,
        },
        {
            "training_stage": "sft",
            "training_domain": "finance",
            "transcript_refinement": True,
            "qa_refinement": False,
            "seeds": 2,
        },
        {
            "training_stage": "sft",
            "training_domain": "finance",
            "transcript_refinement": False,
            "qa_refinement": True,
            "seeds": 2,
        },
        {
            "training_stage": "sft",
            "training_domain": "finance",
            "transcript_refinement": True,
            "qa_refinement": True,
            "seeds": 2,
        },
    ]
    panels = []
    for model, target_rows in rows.items():
        for target, scores in zip(targets, target_rows, strict=True):
            panels.append(
                panel(
                    "shin_kim_2026_speech_sft",
                    f"shin_kim_{model}_{target}",
                    "Table 13",
                    model,
                    target,
                    [
                        arm(arm_id, score, **features)
                        for arm_id, score, features in zip(
                            condition_ids, scores, conditions, strict=True
                        )
                    ],
                    budget_matched=False,
                )
            )
    return panels


def finlcr_2026() -> list[dict]:
    """Recover the curriculum and difficulty-filtering ablations in Tables 2 and 3."""
    panels = []
    component_ids = [
        "short_only",
        "long_only",
        "naive_gspo",
        "s2l_only",
        "das_only",
        "s2l_das_default",
        "s2l_das_upper_0p7",
        "s2l_das_lower_0p3",
    ]
    component_treatments = [
        {"context_sources": 1, "curriculum_progression": False, "difficulty_filtering": False},
        {"context_sources": 1, "curriculum_progression": False, "difficulty_filtering": False},
        {"context_sources": 2, "curriculum_progression": False, "difficulty_filtering": False},
        {"context_sources": 2, "curriculum_progression": True, "difficulty_filtering": False},
        {"context_sources": 2, "curriculum_progression": False, "difficulty_filtering": True},
        {"context_sources": 2, "curriculum_progression": True, "difficulty_filtering": True},
        {"context_sources": 2, "curriculum_progression": True, "difficulty_filtering": True},
        {"context_sources": 2, "curriculum_progression": True, "difficulty_filtering": True},
    ]
    table2 = {
        "short_context_average": [70.44, 70.29, 71.42, 68.57, 67.97, 72.79, 73.57, 73.01],
        "long_context_average": [41.81, 40.06, 39.32, 40.48, 38.71, 42.62, 43.90, 44.39],
    }
    for target, scores in table2.items():
        panels.append(
            panel(
                "finlcr_2026",
                f"finlcr_components_{target}",
                "Table 2",
                "qwen3_4b_thinking_2507",
                target,
                [
                    arm(arm_id, score, **treatment)
                    for arm_id, score, treatment in zip(
                        component_ids, scores, component_treatments, strict=True
                    )
                ],
                budget_matched=False,
            )
        )

    threshold_ids = ["0p2_0p8", "0p3_0p7", "0p1_0p9", "0p2_0p7", "0p3_0p8"]
    train_sizes = [3890, 2222, 7310, 2400, 3712]
    table3 = {
        "finqa": [68.87, 69.96, 70.39, 69.20, 69.52],
        "docfinqa": [47.29, 43.93, 44.14, 46.20, 46.96],
        "docmatheval_complex_long": [30.56, 30.90, 29.20, 29.50, 30.20],
        "docmatheval_complex_short": [77.50, 76.50, 73.00, 77.00, 77.00],
        "docmatheval_simple_long": [50.00, 48.00, 51.00, 56.00, 56.00],
        "docmatheval_simple_short": [72.00, 72.50, 71.50, 74.50, 72.50],
    }
    for target, scores in table3.items():
        panels.append(
            panel(
                "finlcr_2026",
                f"finlcr_thresholds_{target}",
                "Table 3",
                "qwen3_4b_thinking_2507",
                target,
                [
                    arm(
                        arm_id,
                        score,
                        sample_count=sample_count,
                        context_sources=2,
                        curriculum_progression=True,
                        difficulty_filtering=True,
                    )
                    for arm_id, score, sample_count in zip(
                        threshold_ids, scores, train_sizes, strict=True
                    )
                ],
                budget_matched=False,
            )
        )
    return panels


def main() -> None:
    panels = (
        phogat_2024()
        + harsha_2025()
        + fin_prm_2026()
        + fin_sd_2026()
        + shin_kim_2026()
        + finlcr_2026()
    )
    document = {
        "schema_version": 1,
        "status": "source_recovered_before_feature_mapping",
        "normalization_contract": (
            "preserve source-native decision panels; normalize utility only within a panel"
        ),
        "panels": panels,
    }
    OUT.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "sources": len({item["source_id"] for item in panels}),
                "panels": len(panels),
                "arms": sum(len(item["arms"]) for item in panels),
                "output": str(OUT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
