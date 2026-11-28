#!/usr/bin/env python3
"""Build a leakage-safe, multi-target replay of a public Snowball campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "SNOWBALL_CLOSURE_SOURCE.json"
INPUTS = HERE / "SNOWBALL_CLOSURE_INPUTS.jsonl"
LABELS = HERE / "SNOWBALL_CLOSURE_PROTECTED_LABELS.jsonl"
MANIFEST = HERE / "SNOWBALL_CLOSURE_REPLAY.json"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def record_key(candidate_id: str) -> str:
    value = f"marin:snowball:closure:{candidate_id}".encode()
    return "intervention-" + digest_bytes(value)[:24]


def build() -> dict[Path, bytes]:
    source = json.loads(SOURCE.read_text())
    shared = source["shared_contract"]
    candidates = source["sources"]
    if shared["independent_unit"] != "trained intervention":
        raise ValueError("the replay unit must remain the trained intervention")
    if len(candidates) != 3:
        raise ValueError("the released comparison must contain exactly three trained recipes")

    benchmark_names = [set(row["benchmarks"]) for row in candidates]
    if len({tuple(sorted(names)) for names in benchmark_names}) != 1:
        raise ValueError("candidate capability targets differ")
    for benchmark in sorted(benchmark_names[0]):
        baselines = {row["benchmarks"][benchmark]["baseline_mean"] for row in candidates}
        if len(baselines) != 1:
            raise ValueError(f"starting-policy measurement varies for {benchmark}")

    input_rows = []
    label_rows = []
    for candidate in candidates:
        key = record_key(candidate["candidate_id"])
        starting = {
            name: values["baseline_mean"]
            for name, values in sorted(candidate["benchmarks"].items())
        }
        input_rows.append(
            {
                "record_key": key,
                "partition": {
                    "study": "marin_snowball_closure_rlvr",
                    "panel": "two_update_recipe_comparison",
                    "model_family": shared["model_family"],
                },
                "prediction_time": {
                    "candidate_configuration": candidate["treatment"],
                    "optimizer_updates": shared["optimizer_updates"],
                    "starting_policy_measurements": starting,
                },
                "modalities": {
                    "structured_measurements": True,
                    "text": True,
                    "code": False,
                    "curves": False,
                    "trajectories": False,
                    "perceptual_or_structural_assets": False,
                },
                "text": {
                    "candidate_intervention": candidate["candidate_id"].replace("_", " "),
                    "decision_context": "two-update closure and continuation recipe",
                },
            }
        )
        outcomes = []
        for name, values in sorted(candidate["benchmarks"].items()):
            outcomes.append(
                {
                    "metric": name,
                    "higher_is_better": True,
                    "baseline_mean": values["baseline_mean"],
                    "candidate_mean": values["candidate_mean"],
                    "change": values["candidate_mean"] - values["baseline_mean"],
                    "denominator_per_repeat": values["denominator"],
                    "serving_repeats": shared["capability_repeats"],
                }
            )
        label_rows.append(
            {
                "record_key": key,
                "provenance": {
                    "checkpoint": candidate["checkpoint"],
                    "source_path": candidate["path"],
                    "source_sha256": candidate["sha256"],
                },
                "outcomes": outcomes,
            }
        )

    inputs = ("\n".join(canonical(row) for row in input_rows) + "\n").encode()
    labels = ("\n".join(canonical(row) for row in label_rows) + "\n").encode()
    regressions = sum(outcome["change"] < 0 for row in label_rows for outcome in row["outcomes"])
    manifest = {
        "artifact": "anarres_snowball_closure_multi_target_replay_v1",
        "status": "retrospective development replay; not a prospective result",
        "source": {
            "path": SOURCE.name,
            "sha256": digest(SOURCE),
            "repository": source["source_repository"],
            "revision": source["source_revision"],
            "immutable_artifact_hashes": [row["sha256"] for row in candidates],
        },
        "summary": {
            "trained_interventions": len(input_rows),
            "nested_capability_targets": len(benchmark_names[0]),
            "serving_repeats_per_target": shared["capability_repeats"],
            "observed_target_regressions": regressions,
        },
        "artifacts": {
            "inputs": {
                "path": INPUTS.name,
                "rows": len(input_rows),
                "sha256": digest_bytes(inputs),
            },
            "protected_labels": {
                "path": LABELS.name,
                "rows": len(label_rows),
                "sha256": digest_bytes(labels),
            },
        },
        "boundaries": {
            "independence": (
                "one row is one trained recipe; benchmarks and serving repeats remain nested"
            ),
            "leakage": (
                "protected outcomes are stored separately and never copied into model inputs"
            ),
            "scope": (
                "one retrospective Snowball study can test the record contract but cannot "
                "establish transfer"
            ),
            "global_corpus": (
                "not appended to the scalar utility corpus because the outcome is a "
                "capability vector"
            ),
            "mochi": "no Mochi record or outcome is present",
            "modalities": (
                "raw trajectories and curves remain unavailable rather than inferred from summaries"
            ),
        },
    }
    return {
        INPUTS: inputs,
        LABELS: labels,
        MANIFEST: (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.check:
        stale = [
            path
            for path, content in expected.items()
            if not path.exists() or path.read_bytes() != content
        ]
        if stale:
            raise SystemExit("stale Snowball replay: " + ", ".join(map(str, stale)))
        return
    for path, content in expected.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
