"""Pure conversion helpers for OpenAI-compatible Chat Completions."""

from __future__ import annotations

import json
from typing import Any


def content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def build_messages(
    system_prompt: str,
    conversation: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    skip_tool_result_block = False
    for index, item in enumerate(conversation):
        role = item.get("role")
        if role in {"user", "system"}:
            messages.append({"role": role, "content": content(item.get("content"))})
        elif role == "assistant":
            calls = item.get("tool_calls") or []
            call_ids = [f"anarres_call_{index}_{offset}" for offset in range(len(calls))]
            message: dict[str, Any] = {
                "role": "assistant",
                "content": content(item.get("content")),
            }
            if calls:
                message["tool_calls"] = [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call.get("arguments", {}), sort_keys=True),
                        },
                    }
                    for call_id, call in zip(call_ids, calls, strict=True)
                ]
            messages.append(message)
            for call_id, call in zip(call_ids, calls, strict=True):
                if "result" not in call:
                    raise ValueError("canonical tool call is missing its executed result")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": content(call["result"]),
                    }
                )
            skip_tool_result_block = bool(calls)
        elif role == "tool":
            if not skip_tool_result_block:
                raise ValueError("tool result block has no preceding tool calls")
            skip_tool_result_block = False
        else:
            raise ValueError(f"unsupported conversation role: {role!r}")
    return messages


def build_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for tool in tools
    ]
