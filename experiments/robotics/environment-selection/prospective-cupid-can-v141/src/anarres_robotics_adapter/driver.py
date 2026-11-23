"""Source driver for the released RoboMimic Can v1.4.1 dataset.

The native facts below mirror `PROBE_CONTRACT.json`, which is not installed
with the package. A study test keeps them identical.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from anarres.core import EnvironmentSource
from anarres.robotics.contract import EpisodeUnit, RoboticsContractError, SourceDescription

from . import workflow

OBSERVATION_FIELDS = (
    "object",
    "robot0_eef_pos",
    "robot0_eef_quat",
    "robot0_eef_vel_ang",
    "robot0_eef_vel_lin",
    "robot0_gripper_qpos",
    "robot0_gripper_qvel",
    "robot0_joint_pos",
    "robot0_joint_pos_cos",
    "robot0_joint_pos_sin",
    "robot0_joint_vel",
)
HORIZON = 400
PROBE_CONTRACT_SHA256 = "sha256:772ac35411db0dfdbd038f77923b74654c3245f0e58b25888e291c06a61e1b6c"


def source_dataset(source: Path) -> Path:
    """Resolve one unambiguous RoboMimic HDF5 dataset."""

    if source.is_file():
        candidates = [source] if source.suffix.lower() in {".h5", ".hdf5"} else []
    else:
        candidates = sorted(
            item
            for item in source.iterdir()
            if item.is_file() and item.suffix.lower() in {".h5", ".hdf5"}
        )
    if not candidates:
        raise RoboticsContractError(f"no HDF5 dataset found in native source: {source}")
    if len(candidates) > 1:
        raise RoboticsContractError(
            "native source contains multiple HDF5 datasets; place one candidate dataset "
            "in each initialized environment directory"
        )
    return candidates[0]


class RobomimicCanV141Driver:
    native_format = "robomimic-can-v141-hdf5"
    version = "0.6.0"

    def describe(self, source: EnvironmentSource) -> SourceDescription:
        dataset = source_dataset(source.source)
        observed_digest = workflow.file_sha256(dataset)
        if observed_digest != workflow.SOURCE_DATASET_SHA256:
            raise RoboticsContractError(
                "dataset does not match the pinned Can v1.4.1 source artifact: "
                f"sha256:{observed_digest}"
            )
        if source.revision != f"sha256:{observed_digest}":
            raise RoboticsContractError(
                "manifest source revision does not match the dataset content digest"
            )
        import h5py

        with h5py.File(dataset, "r") as handle:
            if "data" not in handle:
                raise RoboticsContractError("RoboMimic dataset is missing the data group")
            demonstrations = sorted(handle["data"].keys(), key=workflow.demo_number)
        if not demonstrations:
            raise RoboticsContractError("RoboMimic dataset contains no demonstrations")
        return SourceDescription(
            environment_id=source.environment_id,
            native_format=self.native_format,
            driver_version=self.version,
            revision=source.revision,
            license=source.license,
            content_digest=f"sha256:{observed_digest}",
            episode_unit=EpisodeUnit(unit="demonstration", grouping_key="demonstration_id"),
            episodes=len(demonstrations),
            observation_fields=OBSERVATION_FIELDS,
            action_fields=("actions",),
            language_field=None,
            task_field=None,
            cost_fields={"control_steps": "step"},
            success_definition="robosuite PickPlaceCan task success; episodes end on success",
            reset_semantics="robosuite environment reset with environment seed 0",
            max_steps=HORIZON,
            evaluation_contract_digest=PROBE_CONTRACT_SHA256,
            missing=("language_instruction", "initial_state_id"),
        )

    def tasks(self, source: EnvironmentSource) -> list[dict[str, Any]]:
        raise RoboticsContractError(
            "the Can v1.4.1 probe contract is specified, but its execution is not released"
        )
