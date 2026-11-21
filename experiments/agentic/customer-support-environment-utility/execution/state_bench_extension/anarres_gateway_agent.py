"""Harness-executed STATE-Bench agent for Chat Completions gateways."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agents.anarres_learning_operator import load_artifact, retrieve
from state_bench.agents.base import AgentRuntimeContext, AgentTurnResponse, BaseAgent

RETRIEVAL_TOOL = {
    "type": "function",
    "name": "retrieve_learnings",
    "description": "Retrieve relevant procedural learnings from prior training tasks.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}
RETRIEVAL_INSTRUCTION = (
    "Before the first substantive answer, use retrieve_learnings when it is available. "
    "Apply only relevant guidance that remains consistent with the current tools and results."
)


class AnarresGatewayAgent(BaseAgent):
    """Use a custom gateway client while STATE-Bench executes domain tools."""

    def __init__(
        self,
        client: Any,
        system_prompt: str,
        tools: list[dict[str, Any]],
        tool_handlers: dict[str, Any],
        runtime_context: AgentRuntimeContext | None = None,
        retrieve_learnings_top_k: int = 3,
        agent_reasoning_effort: str | None = None,
    ):
        del system_prompt, tools, tool_handlers
        super().__init__(runtime_context=runtime_context)
        self.client = client
        self.reasoning_effort = agent_reasoning_effort
        self.retrieve_learnings_top_k = retrieve_learnings_top_k
        self._artifact: dict[str, Any] | None = None

    def _artifact_path(self) -> Path | None:
        value = os.environ.get("ANARRES_STATE_LEARNINGS_PATH", "").strip()
        return Path(value) if value else None

    def memory_tool_schemas(self) -> list[dict[str, Any]]:
        return [RETRIEVAL_TOOL] if self._artifact_path() else []

    def memory_tool_handlers(self) -> dict[str, Any]:
        return {"retrieve_learnings": self._retrieve} if self._artifact_path() else {}

    def _retrieve(self, arguments: dict[str, Any]) -> dict[str, list[str]]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("retrieve_learnings requires a non-empty query")
        path = self._artifact_path()
        if path is None:
            return {"learnings": []}
        if self._artifact is None:
            self._artifact = load_artifact(path)
        return {
            "learnings": retrieve(
                self._artifact,
                query,
                top_k=self.retrieve_learnings_top_k,
            )
        }

    def generate_next_turn(
        self,
        *,
        system_prompt: str,
        conversation: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AgentTurnResponse:
        effective_prompt = system_prompt
        if self._artifact_path():
            effective_prompt = system_prompt.rstrip() + "\n\n" + RETRIEVAL_INSTRUCTION
        response = self.client.generate_agent_turn(
            system_prompt=effective_prompt,
            conversation=conversation,
            tools=tools,
            reasoning_effort=self.reasoning_effort,
        )
        usage = getattr(response, "usage", None)
        self.add_token_usage(
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            reasoning_output_tokens=getattr(
                getattr(usage, "completion_tokens_details", None), "reasoning_tokens", 0
            ),
        )
        message = response.choices[0].message
        calls = []
        for call in message.tool_calls or []:
            calls.append(
                {
                    "name": call.function.name,
                    "arguments": json.loads(call.function.arguments or "{}"),
                }
            )
        return AgentTurnResponse(text=message.content or "", tool_calls=calls)
