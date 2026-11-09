#!/usr/bin/env python3
"""Build matched configuration-generator panels from Hänseroth et al. (2026)."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


SOURCE_ID = "haenseroth_2026_generators"
FORCE_THRESHOLD = 0.05
ENERGY_THRESHOLD = 0.006
GENERATORS = ("grace_oam", "mace_omat", "pet_oam")
SYSTEMS = ("cdp", "cpp", "koh", "lisi", "lpyro", "mos2", "phoh")

# Exact annotations in Supplementary Figure 10. These measurements evaluate the
# candidate generator before it is used to create the 2,000-frame environment.
ZERO_SHOT_FORCE_MAE = {
    "cdp": {"grace_oam": 0.190, "mace_omat": 0.182, "pet_oam": 0.175},
    "cpp": {"grace_oam": 0.195, "mace_omat": 0.197, "pet_oam": 0.179},
    "koh": {"grace_oam": 0.086, "mace_omat": 0.109, "pet_oam": 0.319},
    "lisi": {"grace_oam": 0.085, "mace_omat": 0.080, "pet_oam": 0.104},
    "lpyro": {"grace_oam": 0.353, "mace_omat": 0.424, "pet_oam": 0.277},
    "mos2": {"grace_oam": 0.235, "mace_omat": 0.167, "pet_oam": 0.090},
    "phoh": {"grace_oam": 0.156, "mace_omat": 0.188, "pet_oam": 0.144},
}

PATTERNS = {
    "force_mae_eV_per_A": re.compile(r"Mean absolute force error: ([0-9.eE+-]+)"),
    "relative_force_error": re.compile(r"Mean relative force error: ([0-9.eE+-]+)"),
    "energy_mae_eV_per_atom": re.compile(
        r"Mean absolute energy error per atom: ([0-9.eE+-]+)"
    ),
}


def _parse_errors(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    values = {}
    for key, pattern in PATTERNS.items():
        match = pattern.search(text)
        if match is None:
            raise ValueError(f"missing {key} in {path}")
        values[key] = float(match.group(1))
    return values


def reconstruct(source_root: Path) -> dict:
    manifest_path = source_root / "FETCH_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["artifact"] != "haenseroth_2026_selective_fetch_v1":
        raise ValueError("unexpected fetch manifest")
    provenance = {
        item["relative_path"]: {
            "archive_member": item["archive_member"],
            "crc32": item["crc32"],
        }
        for item in manifest["members"]
    }

    arms = []
    for system in SYSTEMS:
        for generator in GENERATORS:
            relative = f"{generator}/{system}/errors.txt"
            outcomes = _parse_errors(source_root / relative)
            joint_ratio = max(
                outcomes["force_mae_eV_per_A"] / FORCE_THRESHOLD,
                outcomes["energy_mae_eV_per_atom"] / ENERGY_THRESHOLD,
            )
            arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": f"{SOURCE_ID}:{system}:labels2000",
                    "material_system": system,
                    "generator": generator,
                    "dft_label_budget": 2000,
                    "downstream_model": "MACE-MP-0 fine-tune",
                    "pre_outcome_measurements": {
                        "generator_zero_shot_force_mae_eV_per_A": ZERO_SHOT_FORCE_MAE[system][generator],
                        "measurement_source": "Supplementary Figure 10 exact annotation",
                    },
                    "outcome": outcomes
                    | {
                        "joint_threshold_pass": int(
                            outcomes["force_mae_eV_per_A"] < FORCE_THRESHOLD
                            and outcomes["energy_mae_eV_per_atom"] < ENERGY_THRESHOLD
                        ),
                        "joint_threshold_ratio": joint_ratio,
                    },
                    "replication": {"released_training_realizations": 1},
                    "provenance": provenance[relative],
                }
            )

    panels: dict[str, list[dict]] = defaultdict(list)
    for arm in arms:
        panels[arm["panel_id"]].append(arm)
    for panel_arms in panels.values():
        for key, output_key in (
            ("force_mae_eV_per_A", "panel_normalized_force_utility"),
            ("energy_mae_eV_per_atom", "panel_normalized_energy_utility"),
            ("joint_threshold_ratio", "panel_normalized_joint_utility"),
        ):
            values = [arm["outcome"][key] for arm in panel_arms]
            best, worst = min(values), max(values)
            span = worst - best
            for arm in panel_arms:
                value = arm["outcome"][key]
                arm.setdefault("derived", {})[output_key] = (
                    1.0 if span == 0 else (worst - value) / span
                )

    ordered = sorted(arms, key=lambda arm: (arm["panel_id"], arm["generator"]))
    return {
        "artifact": "haenseroth_2026_generator_panels_v1",
        "source_id": SOURCE_ID,
        "panel_count": len(panels),
        "arm_count": len(ordered),
        "matched_contract": {
            "dft_labels": 2000,
            "downstream_model": "MACE-MP-0 fine-tune",
            "force_threshold_eV_per_A": FORCE_THRESHOLD,
            "energy_threshold_eV_per_atom": ENERGY_THRESHOLD,
        },
        "primary_decision_outcome": "joint_threshold_ratio",
        "primary_outcome_definition": "max(force MAE / 0.05, energy MAE / 0.006)",
        "normalization": "within material system; lower native error maps to higher utility",
        "fetch_provenance": {
            "archive_url": manifest["archive_url"],
            "archive_md5_from_zenodo": manifest["archive_md5_from_zenodo"],
            "archive_size_bytes": manifest["archive_size_bytes"],
        },
        "arms": ordered,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = reconstruct(args.source_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
