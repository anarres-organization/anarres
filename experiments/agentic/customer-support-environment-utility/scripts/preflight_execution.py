#!/usr/bin/env python3
"""Check execution readiness without printing credentials or making model calls."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT / "execution/state_bench_extension"

AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_state_bench", Path(__file__).with_name("audit_state_bench.py")
)
AUDIT_MODULE = importlib.util.module_from_spec(AUDIT_SPEC)
assert AUDIT_SPEC.loader is not None
AUDIT_SPEC.loader.exec_module(AUDIT_MODULE)
audit_checkout = AUDIT_MODULE.audit_checkout


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configured(name: str) -> bool:
    return name in os.environ


def preflight(
    checkout: Path,
    provider: str | None = None,
    agent_api_key_var: str | None = None,
    agent_model_name: str | None = None,
) -> dict:
    source = audit_checkout(checkout)
    extension_checks = {}
    for name in ("anarres_learning_operator.py", "anarres_memory_agent.py"):
        expected = EXTENSION_DIR / name
        installed = checkout / "agents" / name
        extension_checks[name] = installed.is_file() and sha256(installed) == sha256(expected)
    evaluator_fields = {
        "STATE_BENCH_EVAL_ENDPOINT": configured("STATE_BENCH_EVAL_ENDPOINT"),
        "STATE_BENCH_EVAL_DEPLOYMENTS": configured("STATE_BENCH_EVAL_DEPLOYMENTS"),
    }
    evaluator_auth_hint = configured("STATE_BENCH_EVAL_API_KEY") or shutil.which("az") is not None
    provider = provider or os.environ.get("STATE_BENCH_AGENT_PROVIDER", "azure_openai").strip()
    agent_api_key_var = agent_api_key_var or os.environ.get(
        "STATE_BENCH_AGENT_API_KEY_VAR",
        "OPENAI_API_KEY" if provider == "openai" else "STATE_BENCH_AGENT_API_KEY",
    )
    model_present = bool(
        (agent_model_name or os.environ.get("STATE_BENCH_AGENT_MODEL", "")).strip()
    )
    if provider == "openai":
        agent_fields = {
            "agent_model_name": model_present,
            "agent_api_key": configured(agent_api_key_var),
        }
    else:
        agent_fields = {
            "agent_model_name": model_present,
            "STATE_BENCH_AGENT_ENDPOINT": configured("STATE_BENCH_AGENT_ENDPOINT"),
            "STATE_BENCH_AGENT_DEPLOYMENTS": configured("STATE_BENCH_AGENT_DEPLOYMENTS"),
            "agent_api_key_or_Azure_auth": configured(agent_api_key_var)
            or shutil.which("az") is not None,
        }
    ready = (
        all(extension_checks.values())
        and all(evaluator_fields.values())
        and evaluator_auth_hint
        and all(agent_fields.values())
        and shutil.which("uv") is not None
    )
    return {
        "schema_version": 1,
        "status": "READY_FOR_TRAIN_SIDE_MODEL_SMOKE" if ready else "BLOCKED_CONFIGURATION",
        "source_revision": source["revision"],
        "extension_checks": extension_checks,
        "uv_available": shutil.which("uv") is not None,
        "evaluator_fields_present": evaluator_fields,
        "evaluator_auth_hint_present": evaluator_auth_hint,
        "agent_provider": provider,
        "agent_fields_present": agent_fields,
        "model_calls_made": 0,
        "credential_values_printed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--agent-provider", choices=["azure_openai", "openai"])
    parser.add_argument("--agent-api-key-var")
    parser.add_argument("--agent-model-name")
    arguments = parser.parse_args()
    result = preflight(
        arguments.checkout.resolve(),
        provider=arguments.agent_provider,
        agent_api_key_var=arguments.agent_api_key_var,
        agent_model_name=arguments.agent_model_name,
    )
    if arguments.output:
        if arguments.output.exists():
            raise FileExistsError(arguments.output)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
