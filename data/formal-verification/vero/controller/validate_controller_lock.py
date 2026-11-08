#!/usr/bin/env python3
"""Validate the isolated Vibe controller used by the frozen Vero probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ControllerLockError(ValueError):
    """Raised when the Vibe controller lock is incomplete or inconsistent."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exactly(mapping: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    if mapping != expected:
        raise ControllerLockError(f"{label} disagrees with the controller lock")


def validate(lock: dict[str, Any], *, lock_path: Path, protocol_path: Path) -> None:
    root = lock_path.parent
    config_path = root / lock["config"]
    agent_path = root / lock["agent"]
    qualification_prompt_path = root / lock["qualification_prompt"]
    if digest(config_path) != lock["config_sha256"]:
        raise ControllerLockError("Vibe config hash disagrees with the controller lock")
    if digest(agent_path) != lock["agent_sha256"]:
        raise ControllerLockError("Lean agent hash disagrees with the controller lock")
    if digest(qualification_prompt_path) != lock["qualification_prompt_sha256"]:
        raise ControllerLockError("qualification prompt hash disagrees with the controller lock")

    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    starting_policy = protocol["starting_policy"]
    design = protocol["probe_design"]
    if lock["agent_scaffold"] != starting_policy["agent_scaffold"]:
        raise ControllerLockError("agent scaffold disagrees with the probe protocol")
    if lock["agent_scaffold_revision"] != starting_policy["agent_scaffold_revision"]:
        raise ControllerLockError("agent revision disagrees with the probe protocol")
    if lock["system_prompt_sha256"] != starting_policy["system_prompt_sha256"]:
        raise ControllerLockError("system-prompt hash disagrees with the probe protocol")
    exactly(
        lock["limits"],
        {
            "maximum_turns": design["maximum_agent_turns_per_attempt"],
            "maximum_cumulative_model_tokens": design[
                "maximum_cumulative_model_tokens_per_attempt"
            ],
            "wall_time_seconds": design["maximum_wall_seconds_per_attempt"],
        },
        "attempt limits",
    )

    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    exactly(
        config,
        {
            "default_agent": "lean",
            "installed_agents": ["lean"],
            "enable_telemetry": False,
            "enable_background_processes": False,
            "enable_auto_update": False,
            "enable_notifications": False,
            "strict_config": True,
        },
        "isolated Vibe config",
    )

    agent = tomllib.loads(agent_path.read_text(encoding="utf-8"))
    providers = agent.pop("providers")
    models = agent.pop("models")
    tools = agent.pop("tools")
    exactly(
        agent,
        {
            "display_name": "Lean (local vLLM)",
            "description": "Lean 4 mode using the frozen local Leanstral endpoint",
            "safety": "neutral",
            "system_prompt_id": "lean",
            "active_model": lock["model_alias"],
        },
        "Lean agent header",
    )
    exactly(
        providers[0],
        {
            "name": "vllm",
            "api_base": lock["api_base"],
            "api_key_env_var": "",
            "backend": "generic",
            "reasoning_field_name": "reasoning_content",
        },
        "Lean agent provider",
    )
    if len(providers) != 1:
        raise ControllerLockError("Lean agent must declare exactly one provider")
    exactly(
        models[0],
        {
            "name": starting_policy["model_id"],
            "provider": "vllm",
            "alias": lock["model_alias"],
            "thinking": starting_policy["reasoning_effort"],
            "temperature": starting_policy["temperature"],
            "auto_compact_threshold": 168000,
        },
        "Lean agent model",
    )
    if len(models) != 1 or tools != {"bash": {"default_timeout": 1200}}:
        raise ControllerLockError("Lean agent tools or model count are not frozen")

    endpoint = urlparse(lock["api_base"])
    if endpoint.scheme != "http" or endpoint.hostname not in {"127.0.0.1", "localhost"}:
        raise ControllerLockError("inference endpoint must be loopback-only HTTP")
    if lock["tool_allowlist"] != ["bash", "edit", "grep", "read_file", "write_file"]:
        raise ControllerLockError("controller tool allowlist is not frozen")
    if lock["environment_allowlist"] != [
        "HOME",
        "LANG",
        "NO_PROXY",
        "PATH",
        "TMPDIR",
        "VIBE_HOME",
        "VIBE_STRICT_CONFIG",
        "XDG_CACHE_HOME",
        "no_proxy",
    ]:
        raise ControllerLockError("controller environment allowlist is not frozen")
    if lock["status"] != "frozen":
        raise ControllerLockError("unexpected controller-lock status")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    validate(
        json.loads(args.lock.read_text(encoding="utf-8")),
        lock_path=args.lock,
        protocol_path=args.protocol,
    )
    print("validated frozen, isolated Vero Vibe controller")


if __name__ == "__main__":
    main()
