#!/usr/bin/env python3
"""Recover matched-budget OMat24 selector panels from Moerman et al."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ID = "moerman_2026_atoms_that_matter"
SELECTORS = ("v14", "DIRECT", "rdm1", "rdm2", "rdm3", "rdm4")
METRICS = {
    "energy_geometric_mean_eV_per_atom": "abs_d_energy_per_atom",
    "force_component_geometric_mean_eV_per_A": "f_mae_comp",
    "stress_voigt_geometric_mean_eV_per_A3": "s_mae_voigt6",
}
DOMAINS = ("bulk", "non_bulk")
ATOM_COUNTS = {
    "v14": 6_566_253,
    "DIRECT": 6_532_238,
    # The four released random subsets contain 6,496,886--6,513,135 atoms.
    # Their exact per-seed mapping is not encoded in paper_tables.json, so the
    # common matched-budget midpoint is recorded without inventing a mapping.
    "rdm1": 6_505_010.5,
    "rdm2": 6_505_010.5,
    "rdm3": 6_505_010.5,
    "rdm4": 6_505_010.5,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(arms: list[dict]) -> None:
    utilities = [arm["derived"]["native_utility"] for arm in arms]
    low, high = min(utilities), max(utilities)
    for arm in arms:
        value = arm["derived"]["native_utility"]
        arm["derived"]["panel_normalized_utility"] = (
            0.5 if high == low else (value - low) / (high - low)
        )


def selector_coordinates(name: str) -> dict:
    return {
        "uses_interpretable_local_environment_coverage": int(name == "v14"),
        "uses_pretrained_latent_space_coverage": int(name == "DIRECT"),
        "uses_random_sampling": int(name.startswith("rdm")),
        "training_atom_count": ATOM_COUNTS[name],
    }


def reconstruct(source_json: Path) -> dict:
    source = json.loads(source_json.read_text(encoding="utf-8"))
    panels: dict[str, list[dict]] = {}
    for endpoint, source_metric in METRICS.items():
        metric = source["metrics"][source_metric]["domains"]
        for domain in DOMAINS:
            block = metric[domain]["geometric_mean"]
            panel_id = f"{SOURCE_ID}:matpes:{domain}:{endpoint}"
            arms = []
            for selector in SELECTORS:
                error = block["values"][selector]
                arm = {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "evaluation_distribution": f"MatPES {domain}",
                    "endpoint": endpoint,
                    "candidate": selector,
                    "selector_family": (
                        "EnvTok"
                        if selector == "v14"
                        else "DIRECT"
                        if selector == "DIRECT"
                        else "random"
                    ),
                    "pre_outcome_measurements": selector_coordinates(selector),
                    "outcome": {"geometric_mean_error": error},
                    "derived": {"native_utility": -error},
                }
                arms.append(arm)
            normalize(arms)
            panels[panel_id] = arms

    arms = [arm for panel_id in sorted(panels) for arm in panels[panel_id]]
    return {
        "artifact": "moerman_2026_omat24_matched_budget_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(panels),
        "arm_count": len(arms),
        "role": "matched-budget selector and random-seed audit; excluded from predictive fitting",
        "normalization": (
            "within MatPES domain and physical endpoint; lower released geometric-mean "
            "error maps to higher utility"
        ),
        "source_artifact": {
            "paper": "https://arxiv.org/abs/2610.14392",
            "repository": "https://github.com/em819/omat24-chemenv-subset",
            "repository_revision": "723696de2c26584b8a907ef900690c0caf3c7b68",
            "path": "09_benchmarks/matpes/paper_tables/paper_tables.json",
            "sha256": sha256(source_json),
        },
        "interpretation_boundary": [
            (
                "EnvTok, DIRECT, and four random subsets hold the training budget near 6.5 "
                "million atoms and use the same MACE training pipeline."
            ),
            (
                "Bulk and non-bulk MatPES outcomes remain separate because the preferred "
                "selector can change with the evaluation distribution."
            ),
            (
                "The paper reports one trained model for EnvTok and DIRECT and four independently "
                "selected random subsets, so selector effects and training variation are not "
                "fully separated."
            ),
            (
                "These released panels test matched-budget selection behavior but do not provide "
                "a new pre-outcome continuous measurement shared by all six arms."
            ),
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_json", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = reconstruct(args.source_json)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("panel_count", "arm_count")}, indent=2))


if __name__ == "__main__":
    main()
