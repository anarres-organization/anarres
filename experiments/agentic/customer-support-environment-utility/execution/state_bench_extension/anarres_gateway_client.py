"""OpenAI-compatible Chat Completions client for STATE-Bench extensions."""

from __future__ import annotations

import json
import os
import threading
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Any

from clients.anarres_gateway_messages import build_messages, build_tools
from openai import OpenAI
from state_bench.client import BaseLLMClient

_LEDGER_LOCK = threading.Lock()
_JOB_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar("anarres_gateway_job", default=None)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set")
    return value


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def set_job_context(*, task_id: str, run_index: int) -> Token:
    """Bind gateway requests to one benchmark job in the current worker context."""
    return _JOB_CONTEXT.set({"task_id": task_id, "run_index": run_index})


def reset_job_context(token: Token) -> None:
    """Restore the worker's previous request-attribution context."""
    _JOB_CONTEXT.reset(token)


class AnarresChatCompletionsClient(BaseLLMClient):
    """Small provider adapter with token-level request accounting."""

    def __init__(self, *, model: str, role: str):
        self.model = model
        self.role = role
        self.base_url = _required_env("ANARRES_GATEWAY_BASE_URL").rstrip("/")
        self._client = OpenAI(
            api_key=_required_env("ANARRES_GATEWAY_API_KEY"),
            base_url=self.base_url,
        )
        self._latest_key_spend_usd: float | None = None

    @classmethod
    def from_env(cls) -> AnarresChatCompletionsClient:
        return cls(model=_required_env("ANARRES_GATEWAY_AGENT_MODEL"), role="agent")

    @property
    def provider_name(self) -> str:
        return "openai_compatible_chat_completions"

    @property
    def model_name(self) -> str:
        return self.model

    @classmethod
    def evaluator_from_env(cls) -> AnarresChatCompletionsClient:
        return cls(model=_required_env("ANARRES_GATEWAY_EVALUATOR_MODEL"), role="evaluator")

    def _record_usage(self, response: Any, purpose: str, headers: Any) -> None:
        ledger_value = os.environ.get("ANARRES_GATEWAY_USAGE_LEDGER", "").strip()
        usage = getattr(response, "usage", None)
        record = {
            **(_JOB_CONTEXT.get() or {}),
            "request_id": getattr(response, "id", None),
            "role": self.role,
            "purpose": purpose,
            "model": getattr(response, "model", None) or self.model,
            "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "response_cost_usd": _optional_float(headers.get("x-litellm-response-cost")),
            "key_spend_usd": _optional_float(headers.get("x-litellm-key-spend")),
            "key_max_budget_usd": _optional_float(headers.get("x-litellm-key-max-budget")),
        }
        self._latest_key_spend_usd = record["key_spend_usd"]
        if not ledger_value:
            return
        ledger = Path(ledger_value)
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with _LEDGER_LOCK, ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _create(
        self,
        *,
        messages: list[dict[str, Any]],
        purpose: str,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        json_mode: bool = False,
        reasoning_effort: str | None = None,
    ) -> Any:
        soft_stop = float(os.environ.get("ANARRES_GATEWAY_SOFT_STOP_USD", "0") or 0)
        if (
            soft_stop > 0
            and self._latest_key_spend_usd is not None
            and self._latest_key_spend_usd >= soft_stop
        ):
            raise RuntimeError(
                f"gateway spend ${self._latest_key_spend_usd:.2f} reached "
                f"the configured ${soft_stop:.2f} soft stop"
            )
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        raw_response = self._client.chat.completions.with_raw_response.create(**kwargs)
        response = raw_response.parse()
        self._record_usage(response, purpose, raw_response.headers)
        return response

    def complete_chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> str:
        # Reasoning-model gateways do not consistently accept temperature.
        del temperature
        response = self._create(
            messages=messages,
            purpose="simulator",
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
    ) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self._create(
            messages=messages,
            purpose="judge",
            max_tokens=max_tokens,
            json_mode=True,
            reasoning_effort=reasoning_effort,
        )
        return json.loads(response.choices[0].message.content or "{}")

    def generate_agent_turn(
        self,
        *,
        system_prompt: str,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        reasoning_effort: str | None,
    ) -> Any:
        return self._create(
            messages=build_messages(system_prompt, conversation),
            purpose="agent_turn",
            max_tokens=4096,
            tools=build_tools(tools),
            reasoning_effort=reasoning_effort,
        )
