#!/usr/bin/env python3
"""Extract and load the frozen weights-only RxnFlow warm-start artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

ARTIFACT_TYPE = "anarres.rxnflow-warm-start-weights.v1"


def extract_weights(checkpoint: Path, output: Path) -> dict[str, Any]:
    """Remove optimizer, replay, scheduler, and RNG state from a checkpoint."""
    import torch

    if checkpoint.resolve() == output.resolve():
        raise ValueError("output must differ from the training checkpoint")
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    required = {
        "rxnflow_version",
        "step",
        "config",
        "environment",
        "model",
        "sampling_model",
        "objectives",
        "condition_dim",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"checkpoint is missing required fields: {missing}")
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "rxnflow_version": payload["rxnflow_version"],
        "source_step": int(payload["step"]),
        "config": payload["config"],
        "environment": payload["environment"],
        "model": payload["model"],
        "sampling_model": payload["sampling_model"],
        "objectives": tuple(payload["objectives"]),
        "source_objectives": tuple(payload["objectives"]),
        "condition_dim": payload["condition_dim"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    torch.save(artifact, temporary)
    temporary.replace(output)
    return artifact


def load_weights(trainer: Any, artifact_path: Path) -> dict[str, Any]:
    """Load policy and EMA weights into a fresh compatible trainer."""
    import torch
    from rxnflow.__version__ import (
        check_library_compatibility,
        check_model_compatibility,
    )

    artifact = torch.load(artifact_path, map_location="cpu", weights_only=False)
    if artifact.get("artifact_type") != ARTIFACT_TYPE:
        raise ValueError("unsupported warm-start artifact")
    check_model_compatibility(artifact["rxnflow_version"])
    check_library_compatibility(artifact["environment"]["rxnflow_version"])
    if trainer.step != 0 or len(trainer.replay) != 0:
        raise ValueError("warm-start weights require a fresh trainer with empty replay")
    if trainer.optimizer.state:
        raise ValueError("warm-start weights require a fresh optimizer")
    if artifact["condition_dim"] != trainer.model.condition_dim:
        raise ValueError("warm-start and target condition dimensions differ")
    if len(artifact["objectives"]) != len(trainer.objectives):
        raise ValueError("warm-start and target objective dimensions differ")
    if (
        artifact["environment"]["content_sha256"] != trainer.env.signature["content_sha256"]
        or artifact["environment"]["synthesis"] != trainer.env.signature["synthesis"]
    ):
        raise ValueError("warm-start and target synthesis environments differ")
    trainer.model.load_state_dict(artifact["model"])
    trainer.sampling_model.load_state_dict(artifact["sampling_model"])
    return {
        "artifact_type": artifact["artifact_type"],
        "rxnflow_version": artifact["rxnflow_version"],
        "source_step": artifact["source_step"],
        "source_objectives": list(artifact["objectives"]),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    artifact = extract_weights(args.checkpoint, args.output)
    print(f"wrote {artifact['artifact_type']} from step {artifact['source_step']} to {args.output}")


if __name__ == "__main__":
    main()
