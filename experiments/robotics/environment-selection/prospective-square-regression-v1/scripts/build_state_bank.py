#!/usr/bin/env python3
"""Create the frozen Square initial-state bank before policy evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import h5py
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pose_feature(pose: np.ndarray) -> np.ndarray:
    """Return x, y, cos(yaw), sin(yaw) from an xyzw object pose."""
    x, y = map(float, pose[:2])
    qx, qy, qz, qw = map(float, pose[3:7])
    sin_yaw = 2.0 * (qw * qz + qx * qy)
    cos_yaw = 1.0 - 2.0 * (qy * qy + qz * qz)
    norm = math.hypot(cos_yaw, sin_yaw)
    if norm == 0.0:
        raise ValueError("object quaternion does not define a planar yaw")
    return np.asarray([x, y, cos_yaw / norm, sin_yaw / norm], dtype=np.float64)


def orientation_offset(feature: np.ndarray) -> float:
    yaw = math.atan2(float(feature[3]), float(feature[2]))
    half_period = math.pi / 4.0
    return abs((yaw + half_period) % (math.pi / 2.0) - half_period)


def assign_strata(features: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    offsets = np.asarray([orientation_offset(row) for row in features])
    medians = {
        "x": float(np.median(features[:, 0])),
        "y": float(np.median(features[:, 1])),
        "orientation_offset": float(np.median(offsets)),
    }
    strata = (
        (features[:, 0] >= medians["x"]).astype(np.int64)
        + 2 * (features[:, 1] >= medians["y"]).astype(np.int64)
        + 4 * (offsets >= medians["orientation_offset"]).astype(np.int64)
    )
    return strata, medians


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise FileExistsError("state-bank outputs must not already exist")

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    expected_hash = protocol["source"]["dataset_sha256"]
    observed_hash = sha256(args.dataset)
    if observed_hash != expected_hash:
        raise ValueError("dataset identity differs from the frozen protocol")

    import robomimic.utils.env_utils as EnvUtils
    import robomimic.utils.file_utils as FileUtils
    import robomimic.utils.obs_utils as ObsUtils
    from robomimic.config import config_factory

    config = config_factory("diffusion_policy")
    ObsUtils.initialize_obs_utils_with_config(config)
    env_meta = FileUtils.get_env_metadata_from_dataset(dataset_path=str(args.dataset))
    if env_meta.get("env_version") != "1.4.1":
        raise ValueError("state bank requires the RoboSuite 1.4.1 contract")
    env = EnvUtils.create_env_from_metadata(
        env_meta=env_meta,
        env_name=env_meta["env_name"],
        render=False,
        render_offscreen=False,
        use_image_obs=False,
    )
    # The model is fixed for this task. Soft resets resample placements without
    # rebuilding the identical MuJoCo model for every state.
    env.env.hard_reset = False

    count = int(protocol["state_bank"]["states"])
    seed = int(protocol["state_bank"]["environment_seed"])
    np.random.seed(seed)
    states: list[np.ndarray] = []
    poses: list[np.ndarray] = []
    model_xml: str | None = None
    for _ in range(count):
        observation = env.reset()
        state = env.get_state()
        current_model = str(state["model"])
        if model_xml is None:
            model_xml = current_model
        elif current_model != model_xml:
            raise ValueError("state resets produced different simulator models")
        states.append(np.asarray(state["states"], dtype=np.float64))
        poses.append(np.asarray(observation["object"][:7], dtype=np.float64))

    state_matrix = np.stack(states)
    pose_matrix = np.stack(poses)
    features = np.stack([pose_feature(row) for row in pose_matrix])
    strata, medians = assign_strata(features)
    stratum_counts = {str(index): int(np.sum(strata == index)) for index in range(8)}
    if any(value == 0 for value in stratum_counts.values()):
        raise ValueError("frozen median splits produced an empty state stratum")
    assert model_xml is not None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(args.output, "w") as output:
        output.create_dataset("states", data=state_matrix)
        output.create_dataset("object_pose_xyzw", data=pose_matrix)
        output.create_dataset("features_xy_cosyaw_sinyaw", data=features)
        output.create_dataset("stratum", data=strata)
        output.attrs["study_id"] = protocol["study_id"]
        output.attrs["environment_seed"] = seed
        output.attrs["source_dataset_sha256"] = observed_hash
        output.attrs["model_xml_sha256"] = hashlib.sha256(model_xml.encode()).hexdigest()
        output.attrs["stratum_medians"] = json.dumps(medians, sort_keys=True)

    manifest = {
        "schema_version": "anarres.robotics-fixed-state-bank.v1",
        "study_id": protocol["study_id"],
        "states": count,
        "environment_seed": seed,
        "state_dimension": int(state_matrix.shape[1]),
        "feature": protocol["state_bank"]["feature"],
        "stratum_medians": medians,
        "stratum_counts": stratum_counts,
        "source_dataset_sha256": observed_hash,
        "state_bank_sha256": sha256(args.output),
        "model_xml_sha256": hashlib.sha256(model_xml.encode()).hexdigest(),
        "candidate_outcomes_opened": False,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
