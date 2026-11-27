"""Deterministic fixture driver for tests and as a reference implementation.

A fixture source is a directory containing `episodes.jsonl`, with one
demonstration per line, and `contract.json`, which states the evaluation
contract. The manifest revision is the SHA-256 digest of `episodes.jsonl`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from anarres.core import EnvironmentSource

from ..contract import EpisodeUnit, RoboticsContractError, SourceDescription, require_text

EPISODE_FIELDS = {
    "demonstration_id",
    "initial_state_id",
    "observation_keys",
    "action_dimension",
    "control_steps",
    "success",
}
CONTRACT_FIELDS = {"success_definition", "reset_semantics", "max_steps", "seeds"}


def _file_digest(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _positive_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RoboticsContractError(f"{field} must be a positive integer")
    return value


class FixtureDriver:
    native_format = "robotics-fixture-v1"
    version = "1.0.0"

    def _read(self, source: EnvironmentSource) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        episodes_path = source.source / "episodes.jsonl"
        contract_path = source.source / "contract.json"
        for path in (episodes_path, contract_path):
            if not path.is_file():
                raise RoboticsContractError(f"fixture source is missing {path.name}")
        if source.revision != _file_digest(episodes_path):
            raise RoboticsContractError("manifest revision does not match episodes.jsonl")
        episodes = [
            json.loads(line)
            for line in episodes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not episodes:
            raise RoboticsContractError("fixture source contains no demonstrations")
        for episode in episodes:
            missing = EPISODE_FIELDS - set(episode)
            if missing:
                raise RoboticsContractError(f"demonstration is missing {sorted(missing)}")
        identities = [episode["demonstration_id"] for episode in episodes]
        if len(set(identities)) != len(identities):
            raise RoboticsContractError("demonstration identities are not unique")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        missing = CONTRACT_FIELDS - set(contract)
        if missing:
            raise RoboticsContractError(f"evaluation contract is missing {sorted(missing)}")
        return episodes, contract

    def describe(self, source: EnvironmentSource) -> SourceDescription:
        episodes, contract = self._read(source)
        observation_keys = {tuple(episode["observation_keys"]) for episode in episodes}
        if len(observation_keys) != 1:
            raise RoboticsContractError("demonstrations disagree on observation fields")
        return SourceDescription(
            environment_id=source.environment_id,
            native_format=self.native_format,
            driver_version=self.version,
            revision=source.revision,
            license=source.license,
            content_digest=_file_digest(source.source / "episodes.jsonl"),
            episode_unit=EpisodeUnit(unit="demonstration", grouping_key="initial_state_id"),
            episodes=len(episodes),
            observation_fields=observation_keys.pop(),
            action_fields=("action",),
            language_field=None,
            task_field="initial_state_id",
            cost_fields={"control_steps": "step"},
            success_definition=require_text(contract["success_definition"], "success_definition"),
            reset_semantics=require_text(contract["reset_semantics"], "reset_semantics"),
            max_steps=_positive_integer(contract["max_steps"], "max_steps"),
            evaluation_contract_digest=_file_digest(source.source / "contract.json"),
            missing=("language_instruction",),
        )

    def tasks(self, source: EnvironmentSource) -> list[dict[str, Any]]:
        episodes, contract = self._read(source)
        states = sorted({episode["initial_state_id"] for episode in episodes})
        return [
            {"task_id": state, "initial_state_id": state, "seeds": list(contract["seeds"])}
            for state in states
        ]
