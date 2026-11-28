#!/usr/bin/env python3
"""Build candidate-level utility views and nested grouped splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RECORD_INPUTS = HERE / "DOMAIN_MODEL_INPUTS.jsonl"
RECORD_LABELS = HERE / "DOMAIN_MODEL_LABELS.jsonl"
RECORD_VIEWS = HERE / "DOMAIN_MODEL_VIEWS.json"
OUTER_SPLITS = HERE / "DOMAIN_SURROGATE_SPLITS.json"
CONTRACT = HERE / "DOMAIN_AWARE_SURROGATE_CONTRACT.json"

UTILITY_INPUTS = HERE / "DOMAIN_AWARE_UTILITY_INPUTS.jsonl"
UTILITY_LABELS = HERE / "DOMAIN_AWARE_UTILITY_LABELS.jsonl"
NESTED_SPLITS = HERE / "DOMAIN_AWARE_NESTED_SPLITS.json"
MANIFEST = HERE / "DOMAIN_AWARE_TRAINING_VIEW.json"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def opaque(prefix: str, *parts: str) -> str:
    digest = sha256_bytes("\x1f".join(parts).encode())[:24]
    return f"{prefix}-{digest}"


def plain_name(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_:-]+", " ", value)).strip()


def key_digest(keys: list[str]) -> str:
    payload = "".join(f"{key}\n" for key in sorted(keys))
    return sha256_bytes(payload.encode())


def nested(value: dict[str, Any], field: str) -> Any:
    current: Any = value
    for part in field.split("."):
        current = current[part]
    return current


def aggregate_candidates() -> list[dict[str, Any]]:
    model_views = json.loads(RECORD_VIEWS.read_text())
    if model_views["inputs"]["sha256"] != sha256(RECORD_INPUTS):
        raise ValueError("domain model-input digest mismatch")
    if model_views["labels"]["sha256"] != sha256(RECORD_LABELS):
        raise ValueError("domain protected-label digest mismatch")

    inputs = {row["join_key"]: row for row in read_jsonl(RECORD_INPUTS)}
    labels = {row["join_key"]: row for row in read_jsonl(RECORD_LABELS)}
    if inputs.keys() != labels.keys():
        raise ValueError("domain input and label joins differ")

    grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for join_key, label in labels.items():
        scoring = label["scoring"]
        grouped[(scoring["study_id"], scoring["panel_id"], scoring["candidate_id"])].append(
            join_key
        )

    candidates = []
    for (study_id, panel_id, candidate_id), join_keys in sorted(grouped.items()):
        feature_encodings = {canonical(inputs[key]["features"]) for key in join_keys}
        if len(feature_encodings) != 1:
            raise ValueError(f"features vary inside candidate {study_id}/{panel_id}/{candidate_id}")
        directions = {labels[key]["outcome"]["higher_is_better"] for key in join_keys}
        metrics = {labels[key]["outcome"]["name"] for key in join_keys}
        if len(directions) != 1 or len(metrics) != 1:
            raise ValueError("outcome contract varies inside one candidate lineage")
        higher_is_better = directions.pop()
        native_values = [float(labels[key]["outcome"]["value"]) for key in join_keys]
        oriented_values = native_values if higher_is_better else [-value for value in native_values]
        features = inputs[join_keys[0]]["features"]
        candidates.append(
            {
                "candidate_key": opaque("candidate", study_id, panel_id, candidate_id),
                "panel_key": opaque("panel", study_id, panel_id),
                "study_key": opaque("study", study_id),
                "study_id": study_id,
                "panel_id": panel_id,
                "candidate_id": candidate_id,
                "domain": features["domain"],
                "evidence_level": features["evidence_level"],
                "record_join_keys": sorted(join_keys),
                "features": features,
                "metric": metrics.pop(),
                "higher_is_better": higher_is_better,
                "native_mean": round(sum(native_values) / len(native_values), 12),
                "oriented_mean": round(sum(oriented_values) / len(oriented_values), 12),
                "training_runs": len(join_keys),
                "cost": labels[join_keys[0]]["cost"],
            }
        )

    panels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        panels[candidate["panel_key"]].append(candidate)
    if any(len(rows) < 2 for rows in panels.values()):
        raise ValueError("utility training panels require at least two candidates")
    for rows in panels.values():
        values = [row["oriented_mean"] for row in rows]
        low, high = min(values), max(values)
        for row in rows:
            row["normalized_utility"] = round(
                0.5 if high == low else (row["oriented_mean"] - low) / (high - low),
                12,
            )
    return candidates


def input_row(candidate: dict[str, Any]) -> dict[str, Any]:
    structured = {
        "domain": candidate["domain"],
        "evidence_level": candidate["evidence_level"],
        "evaluation": {
            "metric": candidate["metric"],
            "higher_is_better": candidate["higher_is_better"],
        },
        "prediction_time_cost": candidate["features"].get("cost", {}),
        "prediction_time_measurements": candidate["features"].get("prediction_time", {}),
    }
    text = {
        "candidate_intervention": plain_name(candidate["candidate_id"]),
        "decision_context": plain_name(candidate["panel_id"]),
    }
    return {
        "candidate_key": candidate["candidate_key"],
        "partition": {
            "panel_key": candidate["panel_key"],
            "study_key": candidate["study_key"],
        },
        "feature_views": {
            "structured": structured,
            "text": text,
        },
        "modalities": {
            "structured_measurements": bool(structured["prediction_time_measurements"]),
            "text": True,
            "code": False,
            "curves": False,
            "trajectories": False,
            "perceptual_or_structural_assets": False,
        },
    }


def label_row(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_key": candidate["candidate_key"],
        "record_join_keys": candidate["record_join_keys"],
        "scoring": {
            "domain": candidate["domain"],
            "study_id": candidate["study_id"],
            "panel_id": candidate["panel_id"],
            "candidate_id": candidate["candidate_id"],
            "evidence_level": candidate["evidence_level"],
            "training_runs": candidate["training_runs"],
        },
        "outcome": {
            "metric": candidate["metric"],
            "higher_is_better": candidate["higher_is_better"],
            "native_mean": candidate["native_mean"],
            "within_panel_normalized_utility": candidate["normalized_utility"],
        },
        "cost": candidate["cost"],
    }


def matches(candidate: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(nested(candidate, field) == expected for field, expected in filters.items())


def split_payload(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    outer = json.loads(OUTER_SPLITS.read_text())
    suites = []
    for suite in outer["suites"]:
        selected = [candidate for candidate in candidates if matches(candidate, suite["filters"])]
        folds = []
        for outer_fold in suite["folds"]:
            field = outer_fold["test_selector"]["field"]
            value = outer_fold["test_selector"]["value"]
            outer_test = [candidate for candidate in selected if nested(candidate, field) == value]
            outer_test_keys = {candidate["candidate_key"] for candidate in outer_test}
            outer_train = [
                candidate
                for candidate in selected
                if candidate["candidate_key"] not in outer_test_keys
            ]
            inner_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for candidate in outer_train:
                inner_groups[str(nested(candidate, suite["group"]))].append(candidate)
            inner_folds = []
            for inner_value, inner_test in sorted(inner_groups.items()):
                inner_test_keys = {candidate["candidate_key"] for candidate in inner_test}
                inner_train = [
                    candidate
                    for candidate in outer_train
                    if candidate["candidate_key"] not in inner_test_keys
                ]
                inner_folds.append(
                    {
                        "fold_id": f"inner-holdout:{inner_value}",
                        "validation_selector": {
                            "field": suite["group"],
                            "value": inner_value,
                        },
                        "train_candidates": len(inner_train),
                        "validation_candidates": len(inner_test),
                        "train_candidate_keys_sha256": key_digest(
                            [candidate["candidate_key"] for candidate in inner_train]
                        ),
                        "validation_candidate_keys_sha256": key_digest(
                            [candidate["candidate_key"] for candidate in inner_test]
                        ),
                        "retrieval_history_candidate_keys_sha256": key_digest(
                            [candidate["candidate_key"] for candidate in inner_train]
                        ),
                    }
                )
            folds.append(
                {
                    "fold_id": outer_fold["fold_id"],
                    "test_selector": outer_fold["test_selector"],
                    "train_candidates": len(outer_train),
                    "test_candidates": len(outer_test),
                    "train_candidate_keys_sha256": key_digest(
                        [candidate["candidate_key"] for candidate in outer_train]
                    ),
                    "test_candidate_keys_sha256": key_digest(
                        [candidate["candidate_key"] for candidate in outer_test]
                    ),
                    "retrieval_history_candidate_keys_sha256": key_digest(
                        [candidate["candidate_key"] for candidate in outer_train]
                    ),
                    "inner_folds": inner_folds,
                }
            )
        suites.append(
            {
                "suite_id": suite["suite_id"],
                "claim": suite["claim"],
                "status": suite["status"],
                "filters": suite["filters"],
                "group": suite["group"],
                "candidates": len(selected),
                "panels": len({candidate["panel_key"] for candidate in selected}),
                "groups": len({nested(candidate, suite["group"]) for candidate in selected}),
                "candidate_keys_sha256": key_digest(
                    [candidate["candidate_key"] for candidate in selected]
                ),
                "folds": folds,
            }
        )
    return {
        "artifact": "anarres_domain_aware_nested_splits_v1",
        "status": "retrospective development splits; not a prospective test",
        "source_outer_splits_sha256": sha256(OUTER_SPLITS),
        "rules": {
            "outer_fold": "hold out the complete study, decision, or domain",
            "inner_fold": (
                "select every model, retrieval, and calibration setting without the "
                "outer test group"
            ),
            "retrieval": "history is restricted to the fitting portion of the active fold",
            "ranking": "candidate outcomes are comparable only inside their native panel",
        },
        "suites": suites,
    }


def render_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical(row) for row in rows) + "\n").encode()


def build() -> dict[Path, bytes]:
    candidates = aggregate_candidates()
    inputs = render_jsonl([input_row(candidate) for candidate in candidates])
    labels = render_jsonl([label_row(candidate) for candidate in candidates])
    splits = (json.dumps(split_payload(candidates), indent=2, sort_keys=True) + "\n").encode()
    modality_counts = Counter()
    for candidate in candidates:
        for modality, available in input_row(candidate)["modalities"].items():
            modality_counts[modality] += int(available)
    manifest = {
        "artifact": "anarres_domain_aware_training_view_v1",
        "status": "deterministic retrospective development view; no learned-model result",
        "sources": {
            "domain_model_inputs_sha256": sha256(RECORD_INPUTS),
            "domain_model_labels_sha256": sha256(RECORD_LABELS),
            "domain_model_views_sha256": sha256(RECORD_VIEWS),
            "domain_surrogate_splits_sha256": sha256(OUTER_SPLITS),
            "domain_aware_contract_sha256": sha256(CONTRACT),
        },
        "utility": {
            "record_rows": len(read_jsonl(RECORD_INPUTS)),
            "candidate_lineages": len(candidates),
            "panels": len({candidate["panel_key"] for candidate in candidates}),
            "studies": len({candidate["study_key"] for candidate in candidates}),
            "domains": dict(
                sorted(Counter(candidate["domain"] for candidate in candidates).items())
            ),
            "modality_availability": dict(sorted(modality_counts.items())),
        },
        "artifacts": {
            "inputs": {
                "path": UTILITY_INPUTS.name,
                "sha256": sha256_bytes(inputs),
                "rows": len(candidates),
            },
            "protected_labels": {
                "path": UTILITY_LABELS.name,
                "sha256": sha256_bytes(labels),
                "rows": len(candidates),
            },
            "nested_splits": {
                "path": NESTED_SPLITS.name,
                "sha256": sha256_bytes(splits),
            },
        },
        "feature_views": {
            "structured": "metadata, metric, prediction-time cost, and native measurements",
            "text": (
                "intervention and decision-context text composed with the structured view "
                "only by methods that declare the text modality"
            ),
        },
        "identity_boundary": (
            "Opaque candidate, panel, and study keys are transport metadata and are not "
            "model features."
        ),
        "modality_boundary": (
            "Unavailable code, curve, trajectory, and perceptual assets remain false rather "
            "than being inferred from summaries."
        ),
        "label_boundary": (
            "Open labels only inside the active training fold; write and hash outer "
            "predictions before scoring."
        ),
        "pretraining_boundary": (
            "Public intervention text may have appeared in pretrained-model data and must "
            "be reported as a contamination risk."
        ),
    }
    return {
        UTILITY_INPUTS: inputs,
        UTILITY_LABELS: labels,
        NESTED_SPLITS: splits,
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
            raise SystemExit("stale domain-aware training view: " + ", ".join(map(str, stale)))
        return
    for path, content in expected.items():
        path.write_bytes(content)


if __name__ == "__main__":
    main()
