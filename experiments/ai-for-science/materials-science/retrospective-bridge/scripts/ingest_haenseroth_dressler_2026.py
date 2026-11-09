#!/usr/bin/env python3
"""Build matched trajectory-stride panels from Hänseroth and Dreßler (2026)."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

SOURCE_ID = "haenseroth_dressler_2026_data_efficiency"
ARXIV_ID = "2608.14899"
ARXIV_SOURCE_SHA256 = "595bc9384c7a104735632074a3aebd6b7d49fa6be63b1a9d102922f3808dd09d"
MAIN_TEX_SHA256 = "509f073ab515e512643b62c0049de48a013733a551cfc508a27a7b3286367749"
SI_TEX_SHA256 = "cdcbcfa9a29ccf799098fb6b9cf428ab14518df365c36e33d254cf76a2f2a633"
METRIC = re.compile(
    r"^\s+mae_(?P<endpoint>f|e):\s+(?P<value>[0-9.eE+-]+)\s*$",
    re.MULTILINE,
)


def read_metric(path: Path) -> dict[str, float]:
    matches = {
        match.group("endpoint"): float(match.group("value"))
        for match in METRIC.finditer(path.read_text())
    }
    if set(matches) != {"e", "f"}:
        raise ValueError(f"unexpected metric file: {path}")
    return matches


def ingest(source: Path) -> dict:
    manifest = json.loads((source / "FETCH_MANIFEST.json").read_text())
    if manifest["artifact"] != "haenseroth_dressler_2026_selective_fetch_v1":
        raise ValueError("unexpected selective-fetch manifest")
    if manifest["archive_count"] != 12 or manifest["selected_member_count"] != 336:
        raise ValueError("incomplete selective-fetch manifest")

    grouped: dict[tuple, dict[int, float]] = defaultdict(dict)
    provenance = []
    for archive in manifest["archives"]:
        mode = archive["training_mode"]
        count = archive["training_configuration_count"]
        stride = archive["trajectory_stride"]
        provenance.append(
            {
                "archive": archive["archive"],
                "archive_md5_from_zenodo": archive["archive_md5_from_zenodo"],
                "archive_size_bytes": archive["archive_size_bytes"],
                "selected_member_count": archive["selected_member_count"],
            }
        )
        for member in archive["members"]:
            metrics = read_metric(source / member["relative_path"])
            for endpoint, value in metrics.items():
                key = (mode, count, member["framework"], member["system"], endpoint)
                grouped[key][stride] = value

    arms = []
    for (mode, count, framework, system, endpoint), values in grouped.items():
        if set(values) != {10, 100}:
            raise ValueError(
                f"incomplete stride pair: {(mode, count, framework, system, endpoint)}"
            )
        best, worst = min(values.values()), max(values.values())
        span = worst - best
        panel_id = (
            f"{SOURCE_ID}:{mode}:n{count}:{framework}:{system}:"
            f"{'force' if endpoint == 'f' else 'energy'}_mae"
        )
        for stride, value in values.items():
            arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": panel_id,
                    "training_mode": mode,
                    "training_configuration_count": count,
                    "framework": framework,
                    "material_system": system,
                    "environment": f"trajectory_stride_{stride}",
                    "endpoint": (
                        "force_mae_eV_per_A" if endpoint == "f" else "energy_mae_eV_per_atom"
                    ),
                    "pre_outcome_measurements": {
                        "trajectory_stride": stride,
                        "trajectory_frame_span": (count - 1) * stride + 1,
                        "relative_trajectory_span": stride / 10.0,
                        "training_configuration_count": count,
                        "uses_pretrained_initialization": int(mode == "finetune"),
                    },
                    "outcome": {"mean_absolute_error": value},
                    "derived": {
                        "native_utility": -value,
                        "panel_normalized_utility": 0.5 if span == 0 else (worst - value) / span,
                        "panel_normalized_regret": 0.0 if span == 0 else (value - best) / span,
                    },
                }
            )

    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "haenseroth_dressler_2026_trajectory_stride_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": f"arXiv:{ARXIV_ID}",
        "data_doi": "10.5281/zenodo.21198813",
        "panel_count": len(grouped),
        "arm_count": len(arms),
        "primary_outcome": "force or energy MAE on the common held-out AIMD trajectory",
        "normalization": "negative MAE, min-max normalized within each matched stride decision",
        "source_files": {
            "arXiv_source_bundle": {"sha256": ARXIV_SOURCE_SHA256},
            "main.tex": {"sha256": MAIN_TEX_SHA256},
            "si.tex": {"sha256": SI_TEX_SHA256},
        },
        "archives": provenance,
        "interpretation_boundary": [
            "Each panel fixes material system, framework, adaptation mode, configuration "
            "count, endpoint, trainer, and test trajectory while changing only AIMD "
            "subsampling stride.",
            "Stride 100 spans a trajectory about ten times longer than stride 10 at the "
            "same DFT-labeled configuration count. Reference-trajectory generation cost "
            "is recorded separately from final label count.",
            "The release contains one trained model per arm. Variation across training "
            "seeds is not recoverable for these stride comparisons.",
            "Energy and force remain separate endpoints because their absolute units and "
            "loss weightings differ.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(args.source)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
