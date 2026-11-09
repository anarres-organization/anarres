#!/usr/bin/env python3
"""Build tungsten label-environment panels from Liu et al. (2026)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

SOURCE_ID = "liu_2026_heterogeneous_uq"
ARXIV_ID = "2507.21297"
REPOSITORY_REVISION = "189443c7263cfbf8530213a24615f41dc86abfd8"
TEST_NOTEBOOK = "Pure W/Test_W_ACE.ipynb"
BUILD_NOTEBOOK = "Pure W/Build_dataset_from_uMLIP_and_DFT.ipynb"
FILE_SHA256 = {
    TEST_NOTEBOOK: "d25f35bb9eada24efdb56690a3c82a154046f9a218cf0f998f8218e67b2e367c",
    BUILD_NOTEBOOK: "b0712a6e174a0ff832482b3d696e8b4084f797a9fed8f03ee47ad111fb120d66",
    "README.md": "5587de6e599f4c30fee8b03987330b492b6925956271775d7a07054f3301c698",
    "LICENSE": "2d9a55c6bedb3b3a06605e551b4cba3bb3efff0e8cdd19eee746e5defe18aba4",
}

# Exact atomic-environment fractions printed by the released construction notebook.
ENVIRONMENTS = {
    0: {"name": "full_dft", "uncertainty_cutoff_eV_per_A": 0.0, "dft_fraction": 1.0},
    1: {
        "name": "uc_0p1",
        "uncertainty_cutoff_eV_per_A": 0.1,
        "dft_fraction": 0.9509667813524879,
    },
    2: {
        "name": "uc_0p5",
        "uncertainty_cutoff_eV_per_A": 0.5,
        "dft_fraction": 0.39364399106657816,
    },
    3: {
        "name": "uc_1",
        "uncertainty_cutoff_eV_per_A": 1.0,
        "dft_fraction": 0.04274561880042655,
    },
    4: {
        "name": "uc_10",
        "uncertainty_cutoff_eV_per_A": 10.0,
        "dft_fraction": 0.027534657250357135,
    },
    5: {
        "name": "all_umlip",
        "uncertainty_cutoff_eV_per_A": math.inf,
        "dft_fraction": 0.0,
    },
}

RESULT_PATTERN = re.compile(
    r"Processing dataset=(?P<dataset>[0-5]), rep=(?P<rep>[0-4]):.*?"
    r"PE RMSE \(eV/atom\): (?P<energy>[0-9.]+).*?"
    r"Force RMSE \(eV/Å\): (?P<force>[0-9.]+)",
    re.DOTALL,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_repository(root: Path) -> None:
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != REPOSITORY_REVISION:
        raise ValueError("unexpected UQ-uMLIP repository revision")
    for relative, expected in FILE_SHA256.items():
        if sha256(root / relative) != expected:
            raise ValueError(f"checksum mismatch for {relative}")


def stream_text(notebook: dict) -> str:
    return "\n".join(
        "".join(output.get("text", []))
        for cell in notebook["cells"]
        for output in cell.get("outputs", [])
        if output.get("output_type") == "stream"
    )


def ingest(repository: Path) -> dict:
    validate_repository(repository)
    notebook = json.loads((repository / TEST_NOTEBOOK).read_text(encoding="utf-8"))
    matches = list(RESULT_PATTERN.finditer(stream_text(notebook)))
    if len(matches) != 30:
        raise ValueError(f"expected 30 completed model evaluations, found {len(matches)}")

    results: dict[tuple[int, str], list[float]] = {}
    for match in matches:
        dataset = int(match.group("dataset"))
        for endpoint in ("energy", "force"):
            results.setdefault((dataset, endpoint), []).append(float(match.group(endpoint)))

    arms = []
    for endpoint, unit in (
        ("energy", "eV_per_atom"),
        ("force", "eV_per_A"),
    ):
        means = {
            dataset: sum(results[(dataset, endpoint)]) / len(results[(dataset, endpoint)])
            for dataset in ENVIRONMENTS
        }
        best, worst = min(means.values()), max(means.values())
        span = worst - best
        for dataset, environment in ENVIRONMENTS.items():
            values = results[(dataset, endpoint)]
            mean = means[dataset]
            arms.append(
                {
                    "source_id": SOURCE_ID,
                    "panel_id": f"{SOURCE_ID}:tungsten_independent_test:{endpoint}_rmse",
                    "material_system": "tungsten",
                    "evaluation_distribution": "independent_defect_plasticity_and_crack_test",
                    "environment": environment["name"],
                    "endpoint": f"{endpoint}_rmse_{unit}",
                    "pre_outcome_measurements": {
                        "uncertainty_cutoff_eV_per_A": (
                            None
                            if math.isinf(environment["uncertainty_cutoff_eV_per_A"])
                            else environment["uncertainty_cutoff_eV_per_A"]
                        ),
                        "dft_atomic_environment_fraction": environment["dft_fraction"],
                        "umlip_atomic_environment_fraction": 1.0 - environment["dft_fraction"],
                        "uses_model_relative_uncertainty_partition": int(dataset in {1, 2, 3, 4}),
                        "matches_independently_validated_uc1_threshold": int(dataset == 3),
                        "training_configuration_count": 1139,
                    },
                    "outcome": {
                        "replicate_rmse": values,
                        "mean_rmse": mean,
                        "independent_initializations": len(values),
                    },
                    "derived": {
                        "native_utility": -mean,
                        "panel_normalized_utility": (worst - mean) / span,
                        "panel_normalized_regret": (mean - best) / span,
                    },
                }
            )

    arms.sort(key=lambda arm: (arm["panel_id"], arm["environment"]))
    return {
        "artifact": "liu_2026_tungsten_label_environment_panels_v1",
        "source_id": SOURCE_ID,
        "source_version": f"arXiv:{ARXIV_ID}",
        "repository_revision": REPOSITORY_REVISION,
        "panel_count": 2,
        "arm_count": 12,
        "primary_outcome": "energy or force RMSE on one independent tungsten test set",
        "source_files": {relative: {"sha256": digest} for relative, digest in FILE_SHA256.items()},
        "interpretation_boundary": [
            "All six environments contain the same 1,139 training configurations "
            "and use the same ACE training and independent test contracts.",
            "The environments vary label provenance and DFT reference cost rather "
            "than configuration identity.",
            "DFT fractions are measured over atomic environments and are not "
            "equivalent to configuration fractions.",
            "The uncertainty threshold was validated across separate public DFT "
            "datasets before the tungsten downstream model comparison.",
            "The two endpoint panels share one material system and one test "
            "distribution, so they provide a source-level stress test rather than "
            "broad materials support.",
        ],
        "arms": arms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = ingest(args.repository)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"panels": payload["panel_count"], "arms": payload["arm_count"]}))


if __name__ == "__main__":
    main()
