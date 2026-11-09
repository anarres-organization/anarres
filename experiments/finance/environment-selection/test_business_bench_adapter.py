#!/usr/bin/env python3

import importlib.util
import io
import tempfile
import urllib.error
from pathlib import Path

SCRIPT = Path(__file__).parent / "adapters" / "business_bench_openai_policy.py"
SPEC = importlib.util.spec_from_file_location("business_bench_openai_policy", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_xml_tool_call_parser() -> None:
    message = {"content": ('<tool_call>{"name":"erp","arguments":{"args":["whoami"]}}</tool_call>')}
    calls = MODULE.parse_tool_calls(message)
    assert calls == [{"id": "xml-call-0", "name": "erp", "arguments": {"args": ["whoami"]}}]


def test_structured_tool_call_parser() -> None:
    message = {
        "tool_calls": [
            {
                "id": "call-7",
                "function": {"name": "list_files", "arguments": '{"path":"."}'},
            }
        ]
    }
    calls = MODULE.parse_tool_calls(message)
    assert calls == [{"id": "call-7", "name": "list_files", "arguments": {"path": "."}}]


def test_erp_command_in_function_name_is_canonicalized() -> None:
    message = {
        "tool_calls": [
            {
                "id": "call-8",
                "function": {"name": "erp get /inbox", "arguments": "{}"},
            }
        ]
    }
    calls = MODULE.parse_tool_calls(message)
    assert calls == [{"id": "call-8", "name": "erp", "arguments": {"args": ["get", "/inbox"]}}]


def test_erp_argument_list_is_canonicalized() -> None:
    name, arguments = MODULE.normalize_tool_call("erp", ["get", "/inbox"])
    assert name == "erp"
    assert arguments == {"args": ["get", "/inbox"]}


def test_unknown_function_name_is_not_canonicalized() -> None:
    name, arguments = MODULE.normalize_tool_call("shell true", {})
    assert name == "shell true"
    assert arguments == {}


def test_malformed_erp_function_name_remains_rejected() -> None:
    name, arguments = MODULE.normalize_tool_call('erp get "unterminated', {})
    assert name == 'erp get "unterminated'
    assert arguments == {}


def test_workspace_tools_and_path_boundary() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary).resolve()
        (workspace / "handbook").mkdir()
        (workspace / "handbook" / "controls.md").write_text("approval required")
        content = MODULE.run_tool("read_file", {"path": "handbook/controls.md"}, workspace)
        assert content == "approval required"
        listing = MODULE.run_tool("list_files", {"path": "handbook"}, workspace)
        assert listing == "handbook/controls.md"
        result = MODULE.run_tool(
            "write_handoff", {"path": "handoff.md", "content": "complete"}, workspace
        )
        assert result == "wrote handoff.md"
        assert (workspace / "handoff.md").read_text() == "complete"
        try:
            MODULE.workspace_path(workspace, "../outside")
        except ValueError as error:
            assert "leaves the task workspace" in str(error)
        else:
            raise AssertionError("workspace traversal was accepted")


def test_missing_workspace_paths_return_tool_observations() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary).resolve()
        assert MODULE.run_tool("read_file", {"path": "missing.md"}, workspace) == (
            "tool_error: requested path is not a file"
        )
        assert MODULE.run_tool("list_files", {"path": "missing"}, workspace) == (
            "tool_error: requested path is not a directory"
        )


def test_unknown_tool_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        try:
            MODULE.run_tool("shell", {"command": "true"}, Path(temporary))
        except ValueError as error:
            assert "unsupported tool" in str(error)
        else:
            raise AssertionError("unknown tool was accepted")


def test_agent_loop_records_tool_trace() -> None:
    responses = iter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "list_files",
                                        "arguments": '{"path":"."}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {"choices": [{"message": {"content": "Work complete."}}]},
        ]
    )
    original = MODULE.request_completion
    MODULE.request_completion = lambda *_args, **_kwargs: next(responses)
    try:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "handbook").mkdir()
            result = MODULE.run_agent(
                workspace,
                "Review the queue.",
                "http://unused",
                "fixture-policy",
                None,
                4,
            )
    finally:
        MODULE.request_completion = original
    assert result["protocol_valid"] is True
    assert result["steps"] == 2
    assert result["events"][0]["tool_results"][0]["name"] == "list_files"
    assert result["final_text"] == "Work complete."
    assert result["usage"]["completion_tokens"] == 0
    assert result["truncated"] is False


def test_context_compaction_preserves_task_and_recent_turn() -> None:
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "old"}]},
        {"role": "tool", "tool_call_id": "old", "content": "x" * 60_000},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "new"}]},
        {"role": "tool", "tool_call_id": "new", "content": "recent"},
    ]
    MODULE.compact_messages(messages)
    assert messages[0]["content"] == "system"
    assert messages[1]["content"] == "task"
    assert messages[-1]["content"] == "recent"
    assert all(message.get("tool_call_id") != "old" for message in messages)


def test_agent_step_limit_is_reported_as_truncation() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {
                                "name": "list_files",
                                "arguments": '{"path":"."}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    original = MODULE.request_completion
    MODULE.request_completion = lambda *_args, **_kwargs: response
    try:
        with tempfile.TemporaryDirectory() as temporary:
            result = MODULE.run_agent(
                Path(temporary),
                "Review the queue.",
                "http://unused",
                "fixture-policy",
                None,
                1,
            )
    finally:
        MODULE.request_completion = original
    assert result["protocol_valid"] is False
    assert result["step_limit_reached"] is True
    assert result["truncated"] is True


def test_endpoint_error_includes_response_detail() -> None:
    original = MODULE.urllib.request.urlopen

    def fail(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "http://unused",
            400,
            "Bad Request",
            {},
            io.BytesIO(b'{"error":"unsupported request"}'),
        )

    MODULE.urllib.request.urlopen = fail
    try:
        try:
            MODULE.request_completion("http://unused", None, {"model": "fixture"})
        except RuntimeError as error:
            assert "HTTP 400" in str(error)
            assert "unsupported request" in str(error)
        else:
            raise AssertionError("endpoint error was not raised")
    finally:
        MODULE.urllib.request.urlopen = original


def test_episode_seed_is_stable() -> None:
    first = MODULE.stable_episode_seed("task__policy__s7__r2")
    second = MODULE.stable_episode_seed("task__policy__s7__r2")
    other = MODULE.stable_episode_seed("task__policy__s7__r3")
    assert first == second
    assert first != other
    assert 0 <= first < 2**31


def test_prior_completion_tokens_are_summed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        run_dir = Path(temporary)
        for turn, tokens in ((1, 120), (2, 80)):
            out = run_dir / "turns" / str(turn) / "out"
            out.mkdir(parents=True)
            (out / "anarres_policy_trace.json").write_text(
                '{"usage":{"completion_tokens":' + str(tokens) + "}}"
            )
        assert MODULE.prior_completion_tokens(run_dir) == 200


if __name__ == "__main__":
    test_xml_tool_call_parser()
    test_structured_tool_call_parser()
    test_erp_command_in_function_name_is_canonicalized()
    test_erp_argument_list_is_canonicalized()
    test_unknown_function_name_is_not_canonicalized()
    test_malformed_erp_function_name_remains_rejected()
    test_workspace_tools_and_path_boundary()
    test_missing_workspace_paths_return_tool_observations()
    test_unknown_tool_is_rejected()
    test_agent_loop_records_tool_trace()
    test_context_compaction_preserves_task_and_recent_turn()
    test_agent_step_limit_is_reported_as_truncation()
    test_endpoint_error_includes_response_detail()
    test_episode_seed_is_stable()
    test_prior_completion_tokens_are_summed()
