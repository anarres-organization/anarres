#!/usr/bin/env python3
"""Validate the frozen GPT-5.6 Sol repeated-measurement protocol against its inputs.

The protocol must name the same policy settings as the qualified harness, the released
task-boundary receipt must still validate against the current route files, and every
frozen input must match its recorded hash. The protocol never authorizes its own
execution.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

STUDY_ROOT = Path(__file__).resolve().parent
PROTOCOL_SCHEMA = "anarres.formal-verification-policy-probe.codex-sol.v1"
ANALYSIS_SCHEMA = "anarres.formal-verification-measurement-analysis.codex-sol.v1"
INHERITED_ESTIMANDS = (
    "advantage_mass",
    "H",
    "zero_signal_rule",
    "cluster_unit",
    "cluster_sensitivity",
    "admission_summary",
)
# Protocol field -> harness constant. The harness file is hash-pinned by the receipt.
HARNESS_SETTINGS = {
    ("starting_policy", "model_id"): "OPENAI_MODEL",
    ("starting_policy", "reasoning_effort"): "REASONING_EFFORT",
    ("starting_policy", "maximum_output_tokens_per_call"): "MAX_COMPLETION_TOKENS",
    ("starting_policy", "harness_version"): "HARNESS_VERSION",
    ("probe_design", "output_token_stop_threshold_per_attempt"): "MAX_TOKENS_PER_ATTEMPT",
    ("probe_design", "maximum_wall_seconds_per_attempt"): "MAX_WALL_SECONDS",
    ("probe_design", "maximum_agent_turns_per_attempt"): "MAX_AGENT_TURNS",
}


class ProtocolError(ValueError):
    """Raised when the frozen protocol disagrees with its inputs."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProtocolError(f"expected an object in {path.name}")
    return value


def load(name: str, path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise ProtocolError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(specification)
    # The harness imports its sibling modules, and dataclasses need a registered module.
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def pinned(root: Path, record: dict[str, Any], name_field: str, hash_field: str) -> Path:
    path = root / record[name_field]
    if not path.is_file() or digest(path) != record[hash_field]:
        raise ProtocolError(f"{record[name_field]} disagrees with its frozen hash")
    return path


def validate_source(protocol: dict[str, Any], root: Path) -> None:
    source = protocol["source"]
    split = read_object(pinned(root, source, "repository_split", "repository_split_sha256"))
    panel = read_object(pinned(root, source, "development_panel", "development_panel_sha256"))
    if panel["source_id"] != source["vero_id"]:
        raise ProtocolError("the development panel and protocol identify different sources")
    pin = read_object(pinned(root, source, "source_pin", "source_pin_sha256"))
    if pin["source_id"] != source["vero_id"] or not source["vero_id"].endswith(pin["commit"]):
        raise ProtocolError("the source pin and protocol identify different sources")
    frozen = {record["benchmark_id"]: record for record in split["repositories"]}
    for record in panel["repositories"]:
        split_record = frozen.get(record["benchmark_id"])
        if split_record is None or split_record["split"] != "development":
            raise ProtocolError("the measurement contains a non-development repository")
        for field in ("directory", "source_language", "specifications"):
            if record[field] != split_record[field]:
                raise ProtocolError(f"panel and split disagree on {field}")
    design = protocol["probe_design"]
    if design["repositories"] != len(panel["repositories"]):
        raise ProtocolError("the protocol has an incorrect repository count")
    expected = (
        len(panel["repositories"])
        * len(design["modes"])
        * design["independent_attempts_per_repository_mode"]
    )
    if design["total_attempts"] != expected:
        raise ProtocolError("the protocol has an incorrect total attempt count")
    tasks = {
        f"{r['benchmark_id']}:{mode}" for r in panel["repositories"] for mode in design["modes"]
    }
    if set(design["task_digests"]) != tasks:
        raise ProtocolError("the frozen task digests must cover exactly the queued tasks")
    if design["scientific_retry_count"] != 0 or design["maximum_infrastructure_retries"] != 1:
        raise ProtocolError("the retry policy must allow one infrastructure retry and no other")


def validate_policy(protocol: dict[str, Any], root: Path) -> None:
    policy = protocol["starting_policy"]
    harness = pinned(root, policy, "harness", "harness_sha256")
    pinned(root, policy, "inference_config", "inference_config_sha256")
    probe = load("vero_codex_sol_protocol_harness", harness)
    for (section, field), constant in HARNESS_SETTINGS.items():
        if protocol[section][field] != getattr(probe, constant):
            raise ProtocolError(f"{section}.{field} disagrees with the qualified harness")
    panel = read_object(root / protocol["source"]["development_panel"])
    harness_panel = [(record["benchmark_id"], record["directory"]) for record in probe.DEV_PANEL]
    if harness_panel != [(r["benchmark_id"], r["directory"]) for r in panel["repositories"]]:
        raise ProtocolError("the harness panel disagrees with the development panel")
    if list(probe.MODES) != protocol["probe_design"]["modes"]:
        raise ProtocolError("the harness modes disagree with the protocol")


def validate_boundary(protocol: dict[str, Any], root: Path) -> None:
    interface = protocol["execution_interface"]
    contract_path = pinned(root, interface, "containment_contract", "containment_contract_sha256")
    receipt_path = pinned(root, interface, "task_boundary_receipt", "task_boundary_receipt_sha256")
    contract = read_object(contract_path)
    receipt = read_object(receipt_path)
    boundary = load(
        "vero_codex_sol_protocol_boundary", STUDY_ROOT / "validate_task_boundary_receipt.py"
    )
    boundary.validate_receipt(receipt, contract, digest(contract_path), bundle=receipt_path.parent)
    boundary.validate_route_files(receipt, root)
    if not receipt["qualified"] or receipt["receipt_id"] != interface["task_boundary_receipt_id"]:
        raise ProtocolError("the protocol must name the qualified task-boundary receipt")
    if receipt["runtime_image"]["image_id"] != interface["runtime_image_id"]:
        raise ProtocolError("the runtime image disagrees with the qualified receipt")
    if (
        receipt["route"]["probe_sha256"]
        != f"sha256:{protocol['starting_policy']['harness_sha256']}"
    ):
        raise ProtocolError("the harness disagrees with the qualified route")
    for record in interface["execution_files"]:
        pinned(root, record, "path", "sha256")


def validate_measurement(protocol: dict[str, Any], root: Path) -> None:
    measurement = protocol["measurement"]
    analysis = read_object(
        pinned(root, measurement, "analysis_contract", "analysis_contract_sha256")
    )
    if analysis.get("schema_version") != ANALYSIS_SCHEMA:
        raise ProtocolError("the analysis contract has an unexpected schema")
    source = analysis["estimand_source"]
    inherited = read_object(pinned(root, source, "analysis_contract", "analysis_contract_sha256"))
    if tuple(source["inherited"]) != INHERITED_ESTIMANDS:
        raise ProtocolError("the analysis contract must inherit every frozen estimand")
    for field in INHERITED_ESTIMANDS:
        if analysis[field] != inherited[field]:
            raise ProtocolError(f"the analysis contract changed the inherited {field}")
    design = protocol["probe_design"]
    if analysis["attempts_per_group"] != design["independent_attempts_per_repository_mode"]:
        raise ProtocolError("the analysis and probe design disagree on attempts")
    repetition = read_object(pinned(root, design, "repetition_design", "repetition_design_sha256"))
    if (
        repetition["selected_attempts_per_repository_mode"]
        != design["independent_attempts_per_repository_mode"]
        or repetition["total_attempts"] != design["total_attempts"]
    ):
        raise ProtocolError("the repetition design and probe design disagree")
    if analysis["maximum_runs_per_entry"] != design["maximum_infrastructure_retries"] + 1:
        raise ProtocolError("the analysis and probe design disagree on retries")
    plan = protocol["cost_plan"]
    screen = read_object(pinned(root, plan, "basis_record", "basis_record_sha256"))
    prices = analysis["cost_reporting"]["planning_prices_usd_per_million_tokens"]
    if screen["planning_prices_usd_per_million_tokens"] != prices:
        raise ProtocolError("the cost plan and analysis use different planning prices")
    screen_usd = sum(
        (
            (attempt["input_tokens"] - attempt["cached_input_tokens"]) * prices["uncached_input"]
            + attempt["cached_input_tokens"] * prices["cached_input"]
            + attempt["output_tokens"] * prices["output"]
        )
        / 1_000_000
        for attempt in screen["attempts"]
    )
    if round(screen_usd, 2) != plan["screen_planning_usd"]:
        raise ProtocolError("the cost plan disagrees with the screen record")
    scoring = analysis["specification_scoring"]
    statuses = set(scoring["strict_reward_one"]) | set(scoring["strict_reward_zero"])
    if scoring["strict_reward_one"] != ["passed"] or len(statuses) != 13:
        raise ProtocolError("only a confirmed pass may earn strict reward")
    if not set(analysis["sensitivity_scoring"]["strict_reward_one"]) <= statuses:
        raise ProtocolError("the sensitivity rule names an unknown status")


def validate(protocol: dict[str, Any], root: Path = STUDY_ROOT) -> None:
    if protocol.get("schema_version") != PROTOCOL_SCHEMA:
        raise ProtocolError("the protocol has an unexpected schema")
    if protocol.get("status") != "frozen_before_model_attempts":
        raise ProtocolError("the protocol is not frozen")
    if protocol.get("execution_authorized") is not False:
        raise ProtocolError("execution is authorized only by a separate record")
    if protocol["measurement"]["qualification_and_prospective_repositories_opened"]:
        raise ProtocolError("qualification and prospective repositories must stay unopened")
    validate_source(protocol, root)
    validate_policy(protocol, root)
    validate_boundary(protocol, root)
    validate_measurement(protocol, root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    validate(read_object(args.protocol), args.protocol.resolve().parent)
    print("validated frozen GPT-5.6 Sol repeated-measurement protocol")


if __name__ == "__main__":
    main()
