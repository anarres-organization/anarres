#!/usr/bin/env python3
"""Run the Vero development screen with GPT-5.6 Sol through OpenAI API.

Orchestrates: materialize → Docker sandbox → agent loop (OpenAI ↔ sandbox) → grade → record.

The Docker sandbox provides the containment boundary: network-denied, read-only root,
workspace-only mounts, no credentials. The controller talks to OpenAI; the sandbox cannot.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from materialize_probe_task import tree_digest, validate_visible_tree
from serve_vibe_sandbox import disk_usage, open_deleted_bytes, remove_tree

# ── Configuration ────────────────────────────────────────────────

OPENAI_MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "xhigh"
MAX_COMPLETION_TOKENS = 16384
MAX_TOKENS_PER_ATTEMPT = 200_000
MAX_WALL_SECONDS = 5400
MAX_AGENT_TURNS = 100
API_REQUEST_TIMEOUT_SECONDS = 1800
HARNESS_VERSION = "1.2.0"

# Task-sandbox route. The containment runner launches this exact command, so a
# change here changes the boundary that must be requalified.
SANDBOX_COMMAND_SECONDS = 300
SANDBOX_MEMORY = "16g"
SANDBOX_CPUS = 4
SANDBOX_PIDS = 256
SANDBOX_FILE_BYTES = 1024 * 1024 * 1024
# The task workspace and the grading build are host directories, so only these budgets
# bound their disk use. Exceeding one is an integrity failure of the attempt.
SANDBOX_WORKSPACE_BYTES = 8 * 1024**3
SANDBOX_WORKSPACE_ENTRIES = 200_000
GRADER_DISK_BYTES = 16 * 1024**3
GRADER_DISK_ENTRIES = 500_000
GRADER_DISK_POLL_SECONDS = 2.0
GRADER_OUTPUT_BYTES = 64 * 1024**2
WORKSPACE_BUDGET_ERROR = -32003
SANDBOX_METHODS = ("sandbox/execute", "sandbox/readFile")
VERO_LAKE_SECONDS = 300
# Above the sum of Vero's own Lake budgets for every development benchmark (two builds,
# up to thirteen axiom-check files twice, and the joint rerender at 300 s each), so a
# slow or rebuilding submission fails inside Vero rather than timing out the stage.
GRADER_SECONDS = 3 * 3600
# Below Vero's own Lake timeout, so a grading container never outlives its stage.
GRADER_LAKE_SECONDS = VERO_LAKE_SECONDS - 10
# Slot bodies may not run code while Lean elaborates them: such code could print a
# forged axiom report or rewrite files that later grading stages compile.
# Attributes whose handlers are toolchain code. Any other attribute can register model
# code with the elaborator, delaborator, or compiler, so a slot body may not use it.
ALLOWED_ATTRIBUTES = (
    "simp",
    "reducible",
    "irreducible",
    "semireducible",
    "inline",
    "noinline",
    "specialize",
    "instance",
    "ext",
    "grind",
    "induction_eliminator",
    "cases_eliminator",
    "match_pattern",
    "elab_as_elim",
    "refl",
    "symm",
    "trans",
    "congr",
    "norm_cast",
    "push_cast",
    "default_instance",
    "wf_preprocess",
)
ELABORATION_PATTERN = (
    r"(?<![\w'.])(?:#[A-Za-z_]+!?|run_cmd|run_elab|run_meta|run_tac|initialize|"
    r"builtin_initialize|elab|elab_rules|macro|macro_rules|syntax|declare_syntax_cat|"
    r"implemented_by|extern|native_decide|by_elab)(?![\w'!?])"
    r"|(?:@\[|attribute\s*\[)[^\]]*\b(?:builtin_)?(?:init|tactic|term_elab|command_elab|"
    r"simproc|dsimproc|delab|app_unexpander|env_linter)\b"
    r"|\bsimproc\b|\bdsimproc\b|\bset_option\s+debug\."
)

DEV_PANEL = [
    {"benchmark_id": "piggybank-v2", "directory": "piggybank", "specs": 23},
    {"benchmark_id": "verified-bitmasks", "directory": "VerifiedBitmasks", "specs": 124},
    {"benchmark_id": "primepy", "directory": "primepy", "specs": 9},
    {"benchmark_id": "arithmetic-v2", "directory": "Arithmetic", "specs": 191},
]

MODES: list[Literal["proof", "codeproof"]] = ["proof", "codeproof"]
ATTEMPTS_PER_REPO_MODE = 1

SANDBOX_SCRIPT = Path(__file__).resolve().parent / "serve_vibe_sandbox.py"
AXIOM_CHECKER = Path(__file__).resolve().parent / "AnarresAxiomCheck.lean"
# One axiom-check file's replay gets the budget Vero gives its compilation, and a
# check that does not finish gets one more run with three times that budget.
AXIOM_CHECK_SECONDS = VERO_LAKE_SECONDS
AXIOM_CHECK_RETRY_SECONDS = 3 * VERO_LAKE_SECONDS


# ── Tool definitions for OpenAI Responses API ───────────────────

TOOLS = [
    {
        "type": "function",
        "name": "sandbox_execute",
        "description": "Execute a shell command in the sandbox workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {
                    "type": "string",
                    "description": "Working directory (absolute path in sandbox)",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout in seconds (optional)",
                },
            },
            "required": ["command", "cwd"],
        },
    },
    {
        "type": "function",
        "name": "sandbox_read_file",
        "description": "Read a file from the sandbox workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file in the sandbox",
                },
                "maxBytes": {
                    "type": "integer",
                    "description": "Maximum bytes to read",
                    "default": 65536,
                },
            },
            "required": ["path"],
        },
    },
]


# ── Sandbox client ───────────────────────────────────────────────


class SandboxClient:
    """JSON-RPC client for serve_vibe_sandbox.py over Unix socket."""

    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self._id = 0

    def _call(self, method: str, params: dict) -> dict:
        self._id += 1
        request = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params})
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_path)
            sock.sendall((request + "\n").encode("utf-8"))
            sock.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = sock.recv(16 * 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
            return json.loads(data)
        finally:
            sock.close()

    def initialize(self) -> dict:
        return self._call("agent/initialize", {"protocolVersion": 2})

    def execute(self, command: str, cwd: str, timeout: float | None = None) -> dict:
        params: dict[str, Any] = {"command": command, "cwd": cwd}
        if timeout is not None:
            params["timeout"] = timeout
        return self._call("sandbox/execute", params)

    def read_file(self, path: str, max_bytes: int = 65536) -> dict:
        return self._call("sandbox/readFile", {"path": path, "maxBytes": max_bytes})


# ── OpenAI Responses API client ─────────────────────────────────


def openai_responses(
    input_items: list[dict],
    *,
    api_key: str,
    api_base: str = "https://api.openai.com/v1",
    timeout: float = API_REQUEST_TIMEOUT_SECONDS,
) -> dict:
    """Call OpenAI Responses API with reasoning effort and tools."""
    import urllib.error
    import urllib.request

    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "input": input_items,
        "tools": TOOLS,
        "reasoning": {"effort": REASONING_EFFORT},
        "max_output_tokens": MAX_COMPLETION_TOKENS,
        "store": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/responses",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = ""
        with contextlib.suppress(Exception):
            body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"OpenAI HTTP {exc.code}: {body}") from exc


# ── Context window management ────────────────────────────────────

CHARS_PER_TOKEN_ESTIMATE = 3.5
MAX_CONTEXT_TOKENS = 128_000
CONTEXT_BUDGET = MAX_CONTEXT_TOKENS - MAX_COMPLETION_TOKENS - 4000


def estimate_item_tokens(item: dict) -> int:
    text = ""
    if isinstance(item.get("content"), str):
        text = item["content"]
    elif isinstance(item.get("content"), list):
        for part in item["content"]:
            if isinstance(part, dict) and part.get("text"):
                text += part["text"]
    if item.get("arguments"):
        text += item["arguments"]
    if item.get("output"):
        text += item["output"]
    if item.get("name"):
        text += item["name"]
    return max(8, int(len(text) / CHARS_PER_TOKEN_ESTIMATE) + 8)


def trim_context(input_items: list[dict], aggressive: bool = False) -> None:
    budget = CONTEXT_BUDGET if not aggressive else CONTEXT_BUDGET - 8000
    total = sum(estimate_item_tokens(item) for item in input_items)
    if total <= budget:
        return
    keep_tail = 8 if not aggressive else 4
    i = 2
    while i < len(input_items) - keep_tail and total > budget:
        item = input_items[i]
        if item.get("type") == "function_call_output":
            old_len = estimate_item_tokens(item)
            item["output"] = "[trimmed]"
            total -= old_len - estimate_item_tokens(item)
        i += 1


# ── Agent loop ───────────────────────────────────────────────────


@dataclass
class AttemptResult:
    attempt_id: str
    benchmark_id: str
    mode: str
    attempt_index: int
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_output_tokens: int = 0
    tool_calls: int = 0
    wall_seconds: float = 0.0
    stop_reason: str = ""
    infrastructure_errors: list[str] = field(default_factory=list)
    grade: dict | None = None
    sandbox_receipt: dict | None = None
    materialization: dict | None = None
    integrity_errors: list[str] = field(default_factory=list)

    @property
    def scored(self) -> bool:
        """Only infrastructure-valid, intact, freshly graded attempts enter the measurement."""
        return (
            not self.infrastructure_errors and not self.integrity_errors and self.grade is not None
        )


class SandboxHalted(RuntimeError):
    """The sandbox stopped because the task outgrew its disk budget."""


def _execute_tool(
    name: str,
    args: dict,
    sandbox: SandboxClient,
    workspace_path: str,
    max_seconds: float | None = None,
) -> str:
    """Dispatch a tool call to the sandbox and return a string result.

    Malformed model arguments are returned to the model as tool errors. They are
    part of the policy's behavior, not infrastructure failures.
    """
    if not isinstance(args, dict):
        return "Error: tool arguments must be a JSON object"
    if name == "sandbox_execute":
        command, cwd, timeout = (
            args.get("command"),
            args.get("cwd", workspace_path),
            args.get("timeout"),
        )
        if not isinstance(command, str) or not isinstance(cwd, str):
            return "Error: sandbox_execute requires string command and cwd"
        if timeout is not None and (
            isinstance(timeout, bool) or not isinstance(timeout, int | float)
        ):
            return "Error: sandbox_execute timeout must be a number"
        if max_seconds is not None:
            timeout = max_seconds if timeout is None else min(timeout, max_seconds)
        rpc_resp = sandbox.execute(command, cwd, timeout)
    elif name == "sandbox_read_file":
        path, max_bytes = args.get("path"), args.get("maxBytes", 65536)
        if (
            not isinstance(path, str)
            or isinstance(max_bytes, bool)
            or not isinstance(max_bytes, int)
        ):
            return "Error: sandbox_read_file requires a string path and integer maxBytes"
        rpc_resp = sandbox.read_file(path, max_bytes)
    else:
        return f"Error: unknown tool: {name}"

    if "result" in rpc_resp:
        content = rpc_resp["result"]
        if name == "sandbox_read_file" and isinstance(content, dict):
            b64 = content.get("contentBase64")
            if b64:
                try:
                    content = base64.b64decode(b64).decode("utf-8", errors="replace")
                except Exception:
                    content = f"[base64 content, {len(b64)} chars]"
            else:
                content = "[file not found]"
    elif "error" in rpc_resp:
        if rpc_resp["error"].get("code") == WORKSPACE_BUDGET_ERROR:
            raise SandboxHalted(rpc_resp["error"].get("message", "workspace budget exceeded"))
        content = f"Error: {rpc_resp['error'].get('message', str(rpc_resp['error']))}"
    else:
        content = json.dumps(rpc_resp)

    if isinstance(content, dict):
        content = json.dumps(content)
    return str(content)[:8_000]


def is_timeout(error: BaseException) -> bool:
    """Recognize a socket timeout, including one wrapped by urllib."""
    import urllib.error

    if isinstance(error, TimeoutError | socket.timeout):
        return True
    return isinstance(error, urllib.error.URLError) and isinstance(
        error.reason, TimeoutError | socket.timeout
    )


def run_agent_loop(
    instruction: str,
    sandbox: SandboxClient,
    workspace_path: str,
    result: AttemptResult,
    api_key: str,
    transcript_path: Path | None = None,
    *,
    responder: Any = None,
    wall_seconds: float | None = None,
) -> None:
    """Run one bounded attempt.

    ``responder`` replaces the Responses API with a deterministic fixture policy and
    ``wall_seconds`` shortens the wall budget; both exist only for containment
    qualification. Model attempts use the defaults.
    """
    respond = openai_responses if responder is None else responder
    wall_budget = MAX_WALL_SECONDS if wall_seconds is None else wall_seconds
    system_prompt = (
        "You are a Lean 4 proof engineer. You have access to a sandbox with a "
        "Lean project. Your workspace is at " + workspace_path + ".\n\n"
        "## Tools\n"
        "Use `sandbox_execute` to run shell commands and `sandbox_read_file` "
        "to read files. Edit files by writing content with shell commands like "
        "`cat > path << 'EOF'\\n...\\nEOF` or using sed.\n\n"
        "## Critical workflow rules\n"
        "1. **Read INSTRUCTION.md first** — it specifies the task, file layout, "
        "marker grammar, and grading rules. Follow it precisely.\n"
        "2. **Read all Spec files** before writing any proof.\n"
        "3. **Compile after every proof** with `lake lean <path>`. Fix errors "
        "immediately. Never batch multiple proofs without compiling between them.\n"
        "4. **One spec at a time.** Fill a stub, compile, fix, then move to the next. "
        "A compiling proof is locked-in progress — never revert it.\n"
        "5. **If a proof fails to compile after two strategies, skip it** and move to "
        "the next spec. Come back later.\n\n"
        "## Environment constraints\n"
        "- The `lake` and `lean` binaries are NOT on the default PATH. Use the full "
        "path: `/opt/elan/bin/lake` and `/opt/elan/bin/lean`. Or run "
        "`export PATH=/opt/elan/bin:$PATH` at the start of each command.\n"
        "- The sandbox has Lean 4 core (`Init`, `Lean`) and `Lake`. There is NO `Std` "
        "library. **Never write `import Std` or `import Std.Tactic.Omega` or any "
        "`Std.*` import.** The `omega` tactic is available from core `Init.Omega` "
        "(auto-imported) — you do NOT need to import it. The `imports` slot should "
        "normally be left empty.\n"
        "- `lake build` only builds modules in the lakefile — it does NOT build or "
        "check proof files. You MUST run `lake lean Primepy/Proof/Primes.lean` "
        "(or the equivalent path) to see if proofs compile. This is the single most "
        "important command. Run it after every change.\n\n"
        "## Common Lean 4 pitfalls\n"
        "- `omega` cannot reason about `Int.ofNat` coercions between `Int` and `Nat`. "
        "Use `simp only [Int.ofNat]` or `push_cast` to normalize before `omega`.\n"
        "- For Int/Nat mixed goals, prefer `norm_cast` or `push_cast` before `omega`.\n"
        "- `grind` is experimental and often fails — prefer `simp`, `omega`, `decide`, "
        "`norm_num` as primary closers.\n"
        "- For list-based specs, decompose with helper lemmas proved by structural "
        "induction, not monolithic tactic blocks.\n"
    )

    input_items: list[dict] = [
        {"role": "developer", "content": system_prompt},
        {"role": "user", "content": instruction},
    ]

    transcript_fh = None
    if transcript_path:
        transcript_fh = open(transcript_path, "w")  # noqa: SIM115 - closed after the loop

    def _log_transcript(entry: dict) -> None:
        if transcript_fh:
            transcript_fh.write(json.dumps(entry) + "\n")
            transcript_fh.flush()

    start = time.monotonic()
    cumulative_output = 0

    def remaining() -> float:
        return wall_budget - (time.monotonic() - start)

    def request() -> dict:
        timeout = min(API_REQUEST_TIMEOUT_SECONDS, remaining())
        return respond(input_items, api_key=api_key, timeout=timeout)

    for turn in range(MAX_AGENT_TURNS):
        if remaining() <= 0:
            result.stop_reason = "wall_time_limit"
            break
        if cumulative_output > MAX_TOKENS_PER_ATTEMPT:
            result.stop_reason = "token_limit"
            break

        trim_context(input_items)
        try:
            response = request()
        except Exception as exc:
            if isinstance(exc, RuntimeError) and "context_length_exceeded" in str(exc).lower():
                trim_context(input_items, aggressive=True)
                try:
                    response = request()
                except Exception as exc2:
                    exc = exc2
                else:
                    exc = None
            if exc is not None:
                # A request still pending when the hard wall deadline expires ends the
                # attempt at its declared wall limit. Every other request failure is
                # an infrastructure failure.
                if remaining() <= 0 and is_timeout(exc):
                    result.stop_reason = "wall_time_limit"
                else:
                    result.infrastructure_errors.append(f"openai: {type(exc).__name__}: {exc}")
                    result.stop_reason = "infrastructure_error"
                break

        usage = response.get("usage", {})
        result.input_tokens += usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        result.output_tokens += output_tokens
        result.cached_input_tokens += usage.get("input_tokens_details", {}).get("cached_tokens", 0)
        result.reasoning_output_tokens += usage.get("output_tokens_details", {}).get(
            "reasoning_tokens", 0
        )
        cumulative_output += output_tokens
        result.turns = turn + 1

        output_items = response.get("output", [])
        function_calls = [item for item in output_items if item.get("type") == "function_call"]

        # Log assistant output
        for oi in output_items:
            if oi.get("type") == "message":
                for part in oi.get("content", []):
                    if part.get("type") == "output_text":
                        _log_transcript(
                            {"turn": turn, "role": "assistant", "text": part["text"][:2000]}
                        )
            elif oi.get("type") == "function_call":
                _log_transcript(
                    {
                        "turn": turn,
                        "role": "tool_call",
                        "name": oi.get("name"),
                        "args": str(oi.get("arguments") or "")[:500],
                    }
                )

        if not function_calls:
            result.stop_reason = response.get("stop_reason", "stop")
            break

        input_items.extend(output_items)

        deadline_reached = False
        for fc in function_calls:
            if remaining() <= 0:
                deadline_reached = True
                break
            result.tool_calls += 1
            name = fc.get("name", "")
            call_id = fc.get("call_id", "")
            try:
                args = json.loads(fc.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps({"error": "invalid JSON arguments"}),
                    }
                )
                continue

            try:
                tool_output = _execute_tool(name, args, sandbox, workspace_path, remaining())
            except SandboxHalted:
                # The policy filled its workspace; the sandbox receipt records why.
                result.stop_reason = "workspace_budget_exceeded"
                break
            except Exception as exc:
                tool_output = f"Sandbox error: {type(exc).__name__}: {exc}"
                result.infrastructure_errors.append(f"sandbox_{name}: {exc}")

            _log_transcript(
                {"turn": turn, "role": "tool_result", "name": name, "output": tool_output[:1000]}
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": tool_output,
                }
            )
        if result.stop_reason == "workspace_budget_exceeded":
            break
        if deadline_reached:
            result.stop_reason = "wall_time_limit"
            break
    else:
        result.stop_reason = "max_turns"

    result.wall_seconds = time.monotonic() - start
    if transcript_fh:
        transcript_fh.close()


# ── Probe orchestrator ────────────────────────────────────────────


def materialize_sandbox(
    vero_root: Path,
    vero_python: str,
    benchmark_id: str,
    benchmark_dir_name: str,
    mode: str,
    output_dir: Path,
) -> Path:
    benchmark_dir = vero_root / "benchmarks" / benchmark_dir_name
    sandbox_dir = output_dir / "source"
    cmd = [
        vero_python,
        "-c",
        f"""
import sys
sys.path.insert(0, "{vero_root / "src"}")
from pathlib import Path
from vero.generation.sandbox import create_sandbox

result = create_sandbox(
    benchmark_dir=Path("{benchmark_dir}"),
    sandbox_dir=Path("{sandbox_dir}"),
    mode="{mode}",
    overwrite=False,
    strip_manifest=True,
    source_context="lean",
)
print("OK", result.sandbox_dir)
""",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"Vero materialize failed: {proc.stderr[:2000]}")
    if not sandbox_dir.exists():
        candidates = list(output_dir.rglob("INSTRUCTION.md"))
        if candidates:
            sandbox_dir = candidates[0].parent
        else:
            raise RuntimeError(f"No sandbox found in {output_dir}")
    return sandbox_dir


def lean_code(text: str) -> str:
    """Return Lean source with comments removed and literal text blanked.

    Comment markers inside strings, raw strings, characters, and quoted names must not
    hide code from the integrity scan, and the code inside an interpolated string's
    braces stays visible.
    """
    out: list[str] = []
    length = len(text)

    def name_character(index: int) -> bool:
        return index >= 0 and (text[index].isalnum() or text[index] in "_'.!?")

    def interpolating(index: int) -> bool:
        # `s!`, `m!`, and `f!` strings, and the message heads that take one directly.
        before = text[:index].rstrip()
        return before.endswith("!") or bool(
            re.search(
                r"(?<![\w.'])(?:throwError|logInfo|logWarning|logError|dbg_trace|trace\[[^\]]*\])$",
                before,
            )
        )

    def literal(index: int, interpolated: bool) -> int:
        while index < length:
            character = text[index]
            if character == "\\":
                index += 2
            elif character == '"':
                return index + 1
            elif interpolated and character == "{":
                out.append(" ")
                index = code(index + 1, inside_braces=True)
                out.append(" ")
            else:
                index += 1
        return length

    def code(index: int, inside_braces: bool = False) -> int:
        depth = 0
        while index < length:
            if text.startswith("--", index):
                newline = text.find("\n", index)
                index = length if newline < 0 else newline
            elif text.startswith("/-", index):
                nesting, index = 1, index + 2
                while index < length and nesting:
                    if text.startswith("/-", index):
                        nesting, index = nesting + 1, index + 2
                    elif text.startswith("-/", index):
                        nesting, index = nesting - 1, index + 2
                    else:
                        index += 1
                out.append(" ")
            elif text[index] == '"':
                out.append('""')
                index = literal(index + 1, interpolated=interpolating(index))
            elif (raw := re.match(r'r(#*)"', text[index:])) and not name_character(index - 1):
                closing = text.find('"' + raw.group(1), index + len(raw.group(0)))
                out.append('""')
                index = length if closing < 0 else closing + 1 + len(raw.group(1))
            elif (
                text[index] == "'"
                and not name_character(index - 1)
                and (character := re.match(r"'(?:\\[^']+|[^'\\])'", text[index:]))
            ):
                out.append("' '")
                index += len(character.group(0))
            elif text[index] == "«":
                closing = text.find("»", index)
                out.append("«name»")
                index = length if closing < 0 else closing + 1
            elif inside_braces and text[index] == "{":
                depth += 1
                out.append("{")
                index += 1
            elif inside_braces and text[index] == "}":
                if depth == 0:
                    return index + 1
                depth -= 1
                out.append("}")
                index += 1
            else:
                out.append(text[index])
                index += 1
        return length

    code(0)
    return "".join(out)


def integrity_violations(slots: list[tuple[str, list[str]]]) -> list[str]:
    """Name the slot bodies that could run model code while Lean builds or loads them."""
    pattern = re.compile(ELABORATION_PATTERN)
    attributes = re.compile(r"@\[([^\]]*)\]|attribute\s*\[([^\]]*)\]")
    found = []
    for file, body_lines in slots:
        source = lean_code("\n".join(body_lines))
        found += [f"{file}: {match.group(0)}" for match in pattern.finditer(source)]
        for group in attributes.findall(source):
            for entry in "".join(group).split(","):
                words = [w for w in entry.replace("-", " ").split() if w not in ("local", "scoped")]
                if words and words[0] not in ALLOWED_ATTRIBUTES:
                    found.append(f"{file}: attribute {words[0]}")
    return sorted(set(found))


class GradeInfrastructureError(RuntimeError):
    """Raised when fresh grading could not run; the attempt then stays unscored."""


def grader_lake_shim(directory: Path, image: str, label: str, docker: str = "docker") -> Path:
    """Write a ``lake`` executable that runs Lake inside the network-denied runtime image.

    Vero's grader invokes every Lean build through ``lake`` on PATH, from inside the
    fresh evaluation directory. Elaboration can execute arbitrary code, so the model's
    slot bodies are compiled only in a container that mounts that one directory.
    """
    executable = shutil.which(docker) or docker
    directory.mkdir(parents=True, exist_ok=True)
    shim = directory / "lake"
    arguments = [
        executable,
        "run",
        "--rm",
        "--label",
        f"anarres.grader={label}",
        "--network",
        "none",
        "--ipc",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(SANDBOX_PIDS),
        "--memory",
        SANDBOX_MEMORY,
        "--cpus",
        str(SANDBOX_CPUS),
        "--user",
        sandbox_user(),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,mode=1777",
        "--tmpfs",
        "/cache:rw,nosuid,nodev,mode=1777",
        "--tmpfs",
        "/dev/mqueue:ro,nosuid,nodev,noexec,size=4k",
        "--env",
        "HOME=/tmp/home",
        "--env",
        "XDG_CACHE_HOME=/cache",
        "--log-driver",
        "none",
        "--entrypoint",
        "/bin/bash",
    ]
    # Lake's output reaches the grader's memory, so each stream is cut at its source; a
    # build that keeps writing past the cut loses its pipe and fails. Both readers are
    # waited for by process id, so no output is lost when the container exits.
    inner = (
        'mkdir -p "$HOME" || exit 125\n'
        "pipes=$(mktemp -d) || exit 125\n"
        'mkfifo "$pipes/out" "$pipes/err" || exit 125\n'
        f'head -c {GRADER_OUTPUT_BYTES} < "$pipes/out" &\n'
        "out=$!\n"
        f'head -c {GRADER_OUTPUT_BYTES} < "$pipes/err" >&2 &\n'
        "err=$!\n"
        f'timeout --kill-after=10s {GRADER_LAKE_SECONDS}s lake "$@" '
        '> "$pipes/out" 2> "$pipes/err"\n'
        "status=$?\n"
        'wait "$out" "$err"\n'
        'exit "$status"\n'
    )
    shim.write_text(
        "#!/bin/sh\n"
        "# Generated by run_codex_sol_probe.py: contained Lake for fresh grading.\n"
        'here="$(pwd -P)"\n'
        'mkdir -p "$here/.lake"\n'
        "exec "
        + " ".join(shlex.quote(argument) for argument in arguments)
        + ' --mount "type=bind,src=$here,dst=$here,readonly"'
        + ' --mount "type=bind,src=$here/.lake,dst=$here/.lake" --workdir "$here" '
        + shlex.quote(image)
        + " -c "
        + shlex.quote(inner)
        + ' lake "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim


def remove_grader_containers(label: str, docker: str = "docker") -> int:
    """Remove grading containers left behind by a killed Lake invocation."""
    executable = shutil.which(docker) or docker
    listed = subprocess.run(
        [executable, "ps", "-aq", "--filter", f"label=anarres.grader={label}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    names = listed.stdout.split()
    if names:
        subprocess.run([executable, "rm", "--force", *names], capture_output=True, timeout=120)
    return len(names)


def escaping_entries(root: Path) -> list[str]:
    """List task entries the host-side grader must not follow or read."""
    resolved_root = root.resolve()
    found = []
    for path in root.rglob("*"):
        if path.is_symlink():
            try:
                target = path.resolve(strict=True)
            except (FileNotFoundError, RuntimeError):
                found.append(path.relative_to(root).as_posix())
                continue
            if not target.is_relative_to(resolved_root):
                found.append(path.relative_to(root).as_posix())
        elif not (path.is_file() or path.is_dir()):
            found.append(path.relative_to(root).as_posix())
    return sorted(found)


def grade_attempt(
    vero_root: Path,
    vero_python: str,
    benchmark_dir: Path,
    source_dir: Path,
    mode: str,
    eval_dir: Path,
    *,
    docker_image: str,
    enforce_integrity: bool = True,
) -> dict:
    """Freshly grade one task, or report the slot bodies that make it ungradable.

    ``enforce_integrity`` is disabled only by containment qualification, to show that
    the contained Lake still holds when elaboration-time code reaches it.
    """
    label = secrets.token_hex(8)
    shim = grader_lake_shim(eval_dir / "contained-bin", docker_image, label)
    environment = {**os.environ, "PATH": f"{shim.parent}{os.pathsep}{os.environ.get('PATH', '')}"}
    cmd = [
        vero_python,
        "-c",
        f"""
import json, re, subprocess, sys
sys.path.insert(0, "{vero_root / "src"}")
from pathlib import Path
from vero.generation.benchmark import Benchmark
from vero.generation.extractor import extract
from vero.evaluation.runner import run_evaluation
from vero.generation.sandbox import create_sandbox

source_dir = Path("{source_dir}")
benchmark_dir = Path("{benchmark_dir}")
eval_dir = Path("{eval_dir}")
mode = "{mode}"

bench = Benchmark(benchmark_dir)
artifact = extract(source_dir, bench, mode=mode)
sys.path.insert(0, "{Path(__file__).resolve().parent}")
from run_codex_sol_probe import integrity_violations
violations = integrity_violations(
    [(slot.file, slot.body_lines) for slot in [*artifact.slots, *artifact.extras]]
) if {enforce_integrity} else []
if violations:
    print(json.dumps({{"integrity_violations": sorted(set(violations))}}))
    sys.exit(0)
result = run_evaluation(
    benchmark_dir=benchmark_dir,
    artifact=artifact,
    mode=mode,
    eval_sandbox_dir=eval_dir / "eval_sandbox",
    report_dir=eval_dir / "eval_report",
    lake_timeout={VERO_LAKE_SECONDS},
)
report = result.report

# Reference build of the untouched task, outside the submission's Lake mount. The
# trusted checker compares statements against it; no model text reaches it.
reference = eval_dir / "reference"
create_sandbox(
    benchmark_dir=benchmark_dir,
    sandbox_dir=reference / "source",
    mode=mode,
    overwrite=False,
    strip_manifest=True,
    source_context="lean",
)
reference_result = run_evaluation(
    benchmark_dir=benchmark_dir,
    artifact=extract(reference / "source", bench, mode=mode),
    mode=mode,
    eval_sandbox_dir=reference / "eval_sandbox",
    report_dir=reference / "eval_report",
    lake_timeout={VERO_LAKE_SECONDS},
)
groups = []
for check in sorted((reference / "eval_sandbox" / "eval").glob("AxiomCheck_*.lean")):
    text = check.read_text()
    groups.append({{
        "roots": re.findall(r"^import (\\S+)$", text, re.M),
        "theorems": re.findall(r"^#print axioms (\\S+)$", text, re.M),
    }})
print(json.dumps({{
    "total_specs": report.summary.total_specs,
    "unfilled_specs": report.summary.unfilled_specs,
    "failed_specs": report.summary.failed_specs,
    "build_ok": report.build_ok,
    "reference_build_ok": reference_result.report.build_ok,
    "vero_passed_specs": report.summary.passed_specs,
    "specs": [
        {{
            "module": s.module,
            "spec": s.spec,
            "status": s.status,
            "kinds": [
                {{"kind": k.kind, "theorem": k.thm_name, "filled": k.filled}} for k in s.kinds
            ],
        }}
        for s in report.specs
    ],
    "groups": groups,
    "allowed_axioms": sorted({{"Classical.choice", "propext", "Quot.sound"}}
                             | set(bench.trusted_axioms or [])),
}}))
""",
    ]
    try:
        result, exceeded = run_with_disk_budget(cmd, environment, eval_dir / "eval_sandbox", label)
    except subprocess.TimeoutExpired as error:
        raise GradeInfrastructureError(f"grader exceeded {GRADER_SECONDS} seconds") from error
    finally:
        leftovers = remove_grader_containers(label)
    if exceeded:
        # Model code filled the build during grading. A container whose client was
        # killed while it started is swept again, the build is removed, and the attempt
        # is an integrity failure, reported apart from infrastructure failures.
        time.sleep(2)
        remove_grader_containers(label)
        remove_tree(eval_dir / "eval_sandbox")
        return {"integrity_violations": [f"grading disk budget exceeded: {exceeded}"]}
    if leftovers:
        raise GradeInfrastructureError(f"{leftovers} grading containers outlived their stage")
    if result.returncode != 0:
        raise GradeInfrastructureError(
            f"grader exited with status {result.returncode}: {result.stderr[:2000]}"
        )
    try:
        grade = json.loads(result.stdout.strip().split("\n")[-1])
    except (json.JSONDecodeError, IndexError) as error:
        raise GradeInfrastructureError(
            f"grader output is unreadable: {result.stdout[:500]}"
        ) from error
    if isinstance(grade, dict) and grade.get("integrity_violations"):
        return grade
    if not isinstance(grade, dict) or not isinstance(grade.get("total_specs"), int):
        raise GradeInfrastructureError("grader output lacks a specification count")
    return apply_axiom_check(grade, eval_dir, docker_image, label)


def run_with_disk_budget(
    command: list[str], environment: dict[str, str], watched: Path, label: str
) -> tuple[subprocess.CompletedProcess[str], str | None]:
    """Run the Vero grader while bounding the disk its contained builds may use.

    The build directory is a host bind mount, so model code that runs while Lake builds
    can write to host disk until this budget stops the grader. Files the build deletes
    while holding them open count too, and so does any path the walk cannot read.
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
        start_new_session=True,
    )
    docker = shutil.which("docker") or "docker"
    exceeded: list[str] = []
    finished = threading.Event()

    def watch() -> None:
        previously_hidden: set[str] = set()
        while not finished.wait(GRADER_DISK_POLL_SECONDS):
            allocated, entries, unreadable = disk_usage(watched)
            listed = subprocess.run(
                [docker, "ps", "-q", "--filter", f"label=anarres.grader={label}"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            ).stdout.split()
            deleted, hiding = 0, set()
            for container in listed:
                held, hides = open_deleted_bytes(docker, container, sandbox_user())
                deleted, hiding = deleted + held, hiding | hides
            # Build processes exit constantly; only one still hiding a poll later counts.
            hidden = bool(hiding & previously_hidden)
            previously_hidden = hiding
            if (
                allocated + deleted > GRADER_DISK_BYTES
                or entries > GRADER_DISK_ENTRIES
                or unreadable
                or hidden
            ):
                exceeded.append(
                    f"{allocated + deleted} bytes ({deleted} deleted but open) and {entries} "
                    f"entries against {GRADER_DISK_BYTES} bytes and {GRADER_DISK_ENTRIES} "
                    f"entries; unreadable paths {unreadable[:3]}; hidden descriptors {hidden}"
                )
                # The grader's Docker clients share its session, so none outlives it.
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                return

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        stdout, stderr = process.communicate(timeout=GRADER_SECONDS)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    finally:
        finished.set()
        watcher.join()
    completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    return completed, (exceeded[0] if exceeded else None)


def library_directories(sandbox: Path) -> list[str]:
    """Return the compiled-library directories of one evaluation sandbox."""
    found = [sandbox / ".lake" / "build" / "lib" / "lean"]
    found += sorted((sandbox / ".lake" / "packages").glob("*/.lake/build/lib/lean"))
    return [str(path) for path in found if path.is_dir()]


def submission_libraries(submission: Path, reference: Path) -> list[str]:
    """Return the submission's library directories at the reference's own paths.

    The submission's ``.lake`` is writable by model code during its build, so only
    directories the untouched build also has, reached without a symbolic link and
    named without a mount separator, are ever mounted into the checker.
    """
    accepted = []
    for library in library_directories(reference):
        relative = Path(library).relative_to(reference)
        candidate = submission / relative
        prefixes = [submission / Path(*relative.parts[: n + 1]) for n in range(len(relative.parts))]
        if (
            "," not in str(candidate)
            and not any(prefix.is_symlink() for prefix in prefixes)
            and candidate.is_dir()
            and candidate.resolve().is_relative_to(submission.resolve())
        ):
            accepted.append(str(candidate))
    return accepted


def run_axiom_check(
    eval_dir: Path, request: dict[str, Any], docker_image: str, label: str
) -> dict[str, dict[str, Any]]:
    """Run the trusted checker once per axiom-check file and return one verdict per theorem.

    The checker reads both builds' compiled libraries as data and never imports a model
    module, so no model code runs while it decides. A check that does not finish
    twice is recorded as incomplete, which grading reports separately from both a
    failed proof and an infrastructure failure. A container that cannot start or a
    reference build that cannot be read is an infrastructure failure.
    """
    check_dir = eval_dir / "axiom-check"
    check_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AXIOM_CHECKER, check_dir / AXIOM_CHECKER.name)
    mounts = [str(check_dir), *request["submission_libraries"], *request["reference_libraries"]]
    base = [
        shutil.which("docker") or "docker",
        "run",
        "--rm",
        "--log-driver",
        "none",
        "--label",
        f"anarres.grader={label}",
        "--network",
        "none",
        "--ipc",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(SANDBOX_PIDS),
        "--memory",
        SANDBOX_MEMORY,
        "--cpus",
        str(SANDBOX_CPUS),
        "--user",
        sandbox_user(),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,mode=1777",
        "--env",
        "HOME=/tmp",
    ]
    for mount in mounts:
        base += ["--mount", f"type=bind,src={mount},dst={mount},readonly"]

    def attempt(index: int, group: dict[str, Any], seconds: int) -> list[dict[str, Any]] | None:
        group_request = {
            key: request[key]
            for key in ("submission_libraries", "reference_libraries", "allowed_axioms")
        } | group
        request_path = check_dir / f"request-{index}.json"
        request_path.write_text(json.dumps(group_request), encoding="utf-8")
        nonce = secrets.token_hex(16)
        command = [
            *base,
            docker_image,
            "timeout",
            "--kill-after=10s",
            f"{seconds}s",
            "lean",
            "--run",
            str(check_dir / AXIOM_CHECKER.name),
            nonce,
            str(request_path),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=seconds + 120
            )
        except subprocess.TimeoutExpired as error:
            raise GradeInfrastructureError("axiom checker container did not stop") from error
        lines = completed.stdout.strip().splitlines()
        if completed.returncode in (125, 126, 127):
            raise GradeInfrastructureError(
                f"axiom checker container failed to start: {completed.stderr[-1000:]}"
            )
        if f"ANARRES-AXIOM-CHECK-REFERENCE-ERROR {nonce}" in lines:
            raise GradeInfrastructureError(
                f"reference build did not load: {completed.stderr[-1000:]}"
            )
        expected = f"ANARRES-AXIOM-CHECK-COMPLETE {nonce} {len(group['theorems'])}"
        if completed.returncode == 0 and lines and lines[-1] == expected:
            return [json.loads(line) for line in lines[:-1]]
        return None

    verdicts: dict[str, dict[str, Any]] = {}
    for index, group in enumerate(request["groups"]):
        reported = attempt(index, group, AXIOM_CHECK_SECONDS)
        if reported is None:
            # A slow host or a transient fault should not decide a theorem, so the check
            # gets one more run with a larger budget before it is recorded as incomplete.
            reported = attempt(index, group, AXIOM_CHECK_RETRY_SECONDS)
        if reported is None:
            reported = [
                {"theorem": name, "ok": False, "incomplete": True, "reason": "check did not finish"}
                for name in group["theorems"]
            ]
        names = [verdict["theorem"] for verdict in reported]
        if sorted(names) != sorted(group["theorems"]):
            raise GradeInfrastructureError("axiom checker did not report each theorem once")
        for verdict in reported:
            # A theorem checked in two files must pass in both.
            previous = verdicts.get(verdict["theorem"])
            if previous is None or previous["ok"]:
                verdicts[verdict["theorem"]] = verdict
    (check_dir / "verdicts.json").write_text(json.dumps(verdicts, indent=1), encoding="utf-8")
    return verdicts


def apply_axiom_check(
    grade: dict[str, Any], eval_dir: Path, docker_image: str, label: str
) -> dict[str, Any]:
    """Downgrade every Vero-passed specification the trusted checker does not confirm."""
    if not grade.get("reference_build_ok"):
        raise GradeInfrastructureError("the reference build of the untouched task failed")
    passed = [spec for spec in grade["specs"] if spec["status"] == "passed"]
    verdicts: dict[str, dict[str, Any]] = {}
    if passed:
        reference = eval_dir / "reference" / "eval_sandbox"
        request = {
            "submission_libraries": submission_libraries(eval_dir / "eval_sandbox", reference),
            "reference_libraries": library_directories(reference),
            "groups": grade["groups"],
            "allowed_axioms": grade["allowed_axioms"],
        }
        verdicts = run_axiom_check(eval_dir, request, docker_image, label)

    def unconfirmed(spec: dict[str, Any]) -> tuple[str, str] | None:
        filled = [kind for kind in spec["kinds"] if kind["filled"]]
        # Vero passes a specification only when exactly one kind is filled.
        if len(filled) != 1:
            return "axiom_recheck_failed", "Vero passed without exactly one filled kind"
        if filled[0]["kind"] == "sat":
            # A grader limit, not a model failure, so it is reported apart from both.
            return "sat_unverified", "a sat claim rests on Vero's uncovered joint rerender"
        verdict = verdicts.get(filled[0]["theorem"])
        if verdict is None:
            return "axiom_recheck_failed", "the filled theorem is in no axiom-check file"
        if verdict["ok"]:
            return None
        if verdict.get("incomplete"):
            return "check_incomplete", verdict["reason"]
        return "axiom_recheck_failed", verdict.get("reason", "rejected")

    specs, downgraded, reasons = [], [], {}
    for spec in grade["specs"]:
        status = spec["status"]
        if status == "passed" and (outcome := unconfirmed(spec)) is not None:
            status = outcome[0]
            downgraded.append(spec["spec"])
            reasons[spec["spec"]] = outcome[1]
        specs.append({"module": spec["module"], "spec": spec["spec"], "status": status})

    def count(status: str) -> int:
        return sum(spec["status"] == status for spec in specs)

    return {
        "total_specs": grade["total_specs"],
        "passed_specs": count("passed"),
        "unfilled_specs": grade["unfilled_specs"],
        "failed_specs": grade["failed_specs"] + count("axiom_recheck_failed"),
        # Neither a pass nor a model failure; the measurement protocol decides how
        # these enter its estimates.
        "check_incomplete_specs": count("check_incomplete"),
        "sat_unverified_specs": count("sat_unverified"),
        "build_ok": grade["build_ok"],
        "vero_passed_specs": grade["vero_passed_specs"],
        "axiom_recheck": {
            "checker": "kernel replay of compiled libraries against a reference build",
            "checked_theorems": len(verdicts),
            "downgraded": downgraded,
            "reasons": reasons,
        },
        "specs": specs,
    }


# ── Task sandbox route ───────────────────────────────────────────


def sandbox_user() -> str:
    """Run the task sandbox as the unprivileged host user, never as container root."""
    return f"{os.getuid()}:{os.getgid()}"


def new_socket_path() -> Path:
    """Return a unique agent-socket path whose directory does not exist yet.

    AF_UNIX paths are limited to about 107 bytes, so the socket lives under /tmp.
    """
    return Path("/tmp") / f"vero-{secrets.token_hex(8)}" / "s.sock"


def sandbox_server_command(
    *,
    python: str,
    socket_path: Path,
    image: str,
    workspace: Path,
    receipt_path: Path,
    container_name_file: Path,
    attempt_id: str,
    task_id: str,
    inference_config_digest: str,
) -> list[str]:
    """Build the exact sandbox-server invocation used for every model attempt."""
    return [
        python,
        str(SANDBOX_SCRIPT),
        "--socket",
        str(socket_path),
        "--image",
        image,
        "--workspace",
        str(workspace),
        "--receipt",
        str(receipt_path),
        "--container-name-file",
        str(container_name_file),
        "--attempt-id",
        attempt_id,
        "--task-id",
        task_id,
        "--model-artifact-digest",
        f"sha256:{hashlib.sha256(OPENAI_MODEL.encode()).hexdigest()}",
        "--inference-config-digest",
        inference_config_digest,
        "--maximum-command-seconds",
        str(SANDBOX_COMMAND_SECONDS),
        "--memory",
        SANDBOX_MEMORY,
        "--cpus",
        str(SANDBOX_CPUS),
        "--pids",
        str(SANDBOX_PIDS),
        "--maximum-file-bytes",
        str(SANDBOX_FILE_BYTES),
        "--maximum-workspace-bytes",
        str(SANDBOX_WORKSPACE_BYTES),
        "--maximum-workspace-entries",
        str(SANDBOX_WORKSPACE_ENTRIES),
        "--user",
        sandbox_user(),
    ]


def remove_leftover_container(container_name_file: Path, docker: str = "docker") -> bool:
    """Remove the attempt container if it outlived its server; return whether one remained.

    The server removes its container on a normal or terminated exit. A killed server
    cannot, so every attempt ends with this backstop.
    """
    if not container_name_file.is_file():
        return False
    name = container_name_file.read_text(encoding="utf-8").strip()
    executable = shutil.which(docker) or docker
    inspected = subprocess.run(
        [executable, "inspect", name], capture_output=True, text=True, timeout=30
    )
    if inspected.returncode != 0:
        return False
    subprocess.run([executable, "rm", "--force", name], capture_output=True, timeout=60)
    return True


def stop_sandbox(
    process: subprocess.Popen, container_name_file: Path, result: AttemptResult
) -> None:
    """Terminate the sandbox server and confirm that its container is gone."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    if remove_leftover_container(container_name_file):
        result.infrastructure_errors.append("sandbox container outlived its server")


def run_one_attempt(
    vero_root: Path,
    vero_python: str,
    docker_image: str,
    benchmark_id: str,
    benchmark_dir_name: str,
    mode: str,
    attempt_index: int,
    probe_root: Path,
    api_key: str,
    inference_config_digest: str,
    *,
    responder: Any = None,
) -> AttemptResult:
    """Run one attempt; ``responder`` replaces the policy only for containment qualification."""
    attempt_id = f"{benchmark_id}_{mode}_a{attempt_index}_{secrets.token_hex(4)}"
    attempt_dir = probe_root / attempt_id
    attempt_dir.mkdir(parents=True, exist_ok=True)

    result = AttemptResult(
        attempt_id=attempt_id,
        benchmark_id=benchmark_id,
        mode=mode,
        attempt_index=attempt_index,
    )

    print(f"\n{'=' * 60}")
    print(f"  Attempt: {attempt_id}")
    print(f"  Benchmark: {benchmark_id} | Mode: {mode} | Index: {attempt_index}")
    print(f"{'=' * 60}")

    # 1. Materialize sandbox
    print("  [1/4] Materializing sandbox...")
    try:
        source_dir = materialize_sandbox(
            vero_root,
            vero_python,
            benchmark_id,
            benchmark_dir_name,
            mode,
            attempt_dir / "run",
        )
        visible = validate_visible_tree(source_dir)
        result.materialization = {
            "task_tree_sha256": tree_digest(source_dir),
            "instruction_sha256": hashlib.sha256(
                (source_dir / "INSTRUCTION.md").read_bytes()
            ).hexdigest(),
            **visible,
        }
        (attempt_dir / "materialization_receipt.json").write_text(
            json.dumps(result.materialization, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        result.infrastructure_errors.append(f"materialize: {exc}")
        result.stop_reason = "infrastructure_error"
        print(f"  FAILED: {exc}")
        return result

    print(f"  Sandbox at: {source_dir}")

    # 2. Start sandbox server
    print("  [2/4] Starting sandbox server...")
    socket_path = new_socket_path()
    socket_dir = socket_path.parent
    receipt_path = attempt_dir / "sandbox_receipt.json"
    container_name_file = attempt_dir / "container-name"
    sandbox_log = attempt_dir / "sandbox_server.log"

    with open(sandbox_log, "w") as sandbox_log_fh:
        sandbox_proc = subprocess.Popen(
            sandbox_server_command(
                python=vero_python,
                socket_path=socket_path,
                image=docker_image,
                workspace=source_dir,
                receipt_path=receipt_path,
                container_name_file=container_name_file,
                attempt_id=attempt_id,
                task_id=f"{benchmark_id}:{mode}",
                inference_config_digest=inference_config_digest,
            ),
            stdout=sandbox_log_fh,
            stderr=subprocess.STDOUT,
        )

    # Docker may take up to two minutes to create and inspect the container.
    for _ in range(360):
        if socket_path.exists():
            break
        if sandbox_proc.poll() is not None:
            log_tail = sandbox_log.read_text()[-2000:] if sandbox_log.exists() else "no log"
            result.infrastructure_errors.append(f"sandbox server exited early: {log_tail}")
            result.stop_reason = "infrastructure_error"
            stop_sandbox(sandbox_proc, container_name_file, result)
            print(f"  FAILED: sandbox server died. Log:\n{log_tail[:500]}")
            return result
        time.sleep(0.5)
    else:
        log_tail = sandbox_log.read_text()[-2000:] if sandbox_log.exists() else "no log"
        result.infrastructure_errors.append(f"sandbox socket did not appear in 180s: {log_tail}")
        result.stop_reason = "infrastructure_error"
        stop_sandbox(sandbox_proc, container_name_file, result)
        print(f"  FAILED: socket timeout. Log:\n{log_tail[:500]}")
        return result

    sandbox = SandboxClient(str(socket_path))

    try:
        init_resp = sandbox.initialize()
        workspace_path = init_resp.get("result", {}).get("workspace", "/workspace")
    except Exception as exc:
        result.infrastructure_errors.append(f"sandbox init: {exc}")
        result.stop_reason = "infrastructure_error"
        stop_sandbox(sandbox_proc, container_name_file, result)
        print(f"  FAILED: sandbox init: {exc}")
        return result

    print(f"  Sandbox ready, workspace: {workspace_path}")

    # The policy must receive the exact materialized instruction or no attempt runs.
    try:
        instr_resp = sandbox.read_file(f"{workspace_path}/INSTRUCTION.md", 100_000)
        instruction_bytes = base64.b64decode(instr_resp["result"]["contentBase64"])
        if (
            hashlib.sha256(instruction_bytes).hexdigest()
            != result.materialization["instruction_sha256"]
        ):
            raise ValueError("sandbox instruction differs from the materialized task")
        instruction = instruction_bytes.decode("utf-8")
    except Exception as exc:
        result.infrastructure_errors.append(f"instruction: {exc}")
        result.stop_reason = "infrastructure_error"
        stop_sandbox(sandbox_proc, container_name_file, result)
        print(f"  FAILED: instruction: {exc}")
        return result

    # 3. Run agent loop
    print(f"  [3/4] Running agent loop (max {MAX_AGENT_TURNS} turns, {MAX_WALL_SECONDS}s)...")
    transcript_path = attempt_dir / "transcript.jsonl"
    try:
        run_agent_loop(
            instruction,
            sandbox,
            workspace_path,
            result,
            api_key,
            transcript_path,
            responder=responder,
        )
    except Exception as exc:
        result.infrastructure_errors.append(f"agent loop: {type(exc).__name__}: {exc}")
        result.stop_reason = "infrastructure_error"
    print(
        f"  Agent done: {result.turns} turns, {result.output_tokens} output tokens "
        f"({result.reasoning_output_tokens} reasoning), "
        f"{result.tool_calls} tool calls, {result.wall_seconds:.1f}s, "
        f"stop={result.stop_reason}"
    )

    stop_sandbox(sandbox_proc, container_name_file, result)
    shutil.rmtree(socket_dir, ignore_errors=True)

    if receipt_path.exists():
        result.sandbox_receipt = json.loads(receipt_path.read_text())
        for error in result.sandbox_receipt.get("infrastructure_errors") or []:
            result.infrastructure_errors.append(f"sandbox: {error}")
    else:
        result.infrastructure_errors.append("sandbox receipt is missing")

    exceeded = (result.sandbox_receipt or {}).get("workspace_budget_exceeded")
    if exceeded:
        # The policy filled its workspace. The oversized tree is never graded, and it is
        # removed so it cannot hold host disk that later attempts need.
        result.integrity_errors.append(f"workspace disk budget exceeded: {exceeded}")
        remove_tree(source_dir)
        print("  Not graded: the workspace exceeded its disk budget.")
        return result

    # The host-side extractor must never follow a link out of the task.
    escaped = escaping_entries(source_dir)
    if escaped:
        result.integrity_errors.append(
            f"task contains entries outside the boundary: {escaped[:10]}"
        )

    # 4. Grade. Infrastructure-invalid attempts are excluded rather than scored zero.
    if result.infrastructure_errors or result.integrity_errors:
        print("  [4/4] Skipping fresh grade: the attempt is not scoreable.")
        return result
    print("  [4/4] Grading...")
    try:
        benchmark_dir = vero_root / "benchmarks" / benchmark_dir_name
        grade = grade_attempt(
            vero_root,
            vero_python,
            benchmark_dir,
            source_dir,
            mode,
            attempt_dir / "eval",
            docker_image=docker_image,
        )
        if grade.get("integrity_violations"):
            result.integrity_errors.append(
                f"grading integrity: {grade['integrity_violations'][:10]}"
            )
            print("  Not graded: the slot bodies or their build broke the grading boundary.")
            return result
        result.grade = grade
        print(
            f"  Grade: {grade['passed_specs']}/{grade['total_specs']} specs passed, "
            f"build_ok={grade.get('build_ok')}"
        )
    except Exception as exc:
        result.infrastructure_errors.append(f"grade: {exc}")
        print(f"  Grade FAILED: {exc}")

    return result


def summarize(results: list[AttemptResult]) -> dict[str, Any]:
    """Aggregate only scored attempts; infrastructure failures are reported separately."""
    scored = [r for r in results if r.scored]
    total_passed = sum(r.grade["passed_specs"] for r in scored)
    total_specs = sum(r.grade["total_specs"] for r in scored)
    repos_with_nonzero = sorted({r.benchmark_id for r in scored if r.grade["passed_specs"] > 0})
    pooled_rate = total_passed / total_specs if total_specs > 0 else None
    return {
        "total_attempts": len(results),
        "scored_attempts": len(scored),
        "infrastructure_invalid_attempts": sum(bool(r.infrastructure_errors) for r in results),
        "integrity_invalid_attempts": sum(
            bool(r.integrity_errors) and not r.infrastructure_errors for r in results
        ),
        "ungraded_attempts": sum(
            r.grade is None and not r.infrastructure_errors and not r.integrity_errors
            for r in results
        ),
        "total_passed_specs": total_passed,
        "total_specs": total_specs,
        # Specifications neither passed nor failed: the checker could not finish, or a
        # sat claim rests on Vero's uncovered joint rerender. Reported, never pooled.
        "check_incomplete_specs": sum(r.grade.get("check_incomplete_specs", 0) for r in scored),
        "sat_unverified_specs": sum(r.grade.get("sat_unverified_specs", 0) for r in scored),
        "repos_with_nonzero_coverage": repos_with_nonzero,
        "pooled_strict_rate": None if pooled_rate is None else round(pooled_rate, 4),
        "screen_pass": (
            len(scored) == len(results)
            and len(repos_with_nonzero) >= 2
            and pooled_rate is not None
            and pooled_rate < 0.80
        ),
        "per_attempt": [
            {
                "attempt_id": r.attempt_id,
                "benchmark_id": r.benchmark_id,
                "mode": r.mode,
                "scored": r.scored,
                "turns": r.turns,
                "output_tokens": r.output_tokens,
                "reasoning_output_tokens": r.reasoning_output_tokens,
                "tool_calls": r.tool_calls,
                "wall_seconds": round(r.wall_seconds, 2),
                "stop_reason": r.stop_reason,
                "passed_specs": r.grade["passed_specs"] if r.scored else None,
                "total_specs": r.grade["total_specs"] if r.scored else None,
                "check_incomplete_specs": r.grade.get("check_incomplete_specs")
                if r.scored
                else None,
                "sat_unverified_specs": r.grade.get("sat_unverified_specs") if r.scored else None,
                "infrastructure_errors": r.infrastructure_errors,
                "integrity_errors": r.integrity_errors,
            }
            for r in results
        ],
    }


def compute_inference_config_digest(config_path: Path) -> str:
    content = config_path.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def main():
    parser = argparse.ArgumentParser(description="Run Vero development screen with GPT-5.6 Sol")
    parser.add_argument("--vero-root", type=Path, required=True)
    parser.add_argument(
        "--vero-python", type=str, required=True, help="Path to the Vero Python interpreter"
    )
    parser.add_argument("--probe-root", type=Path, required=True)
    parser.add_argument(
        "--docker-image", type=str, required=True, help="Docker image digest (sha256:...)"
    )
    parser.add_argument(
        "--smoke-test", action="store_true", help="Run 1 attempt only (primepy proof)"
    )
    parser.add_argument("--benchmark", type=str, default=None, help="Run only this benchmark_id")
    parser.add_argument(
        "--mode", type=str, default=None, help="Run only this mode (proof or codeproof)"
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    vero_root = args.vero_root.resolve()
    probe_root = args.probe_root.resolve()
    probe_root.mkdir(parents=True, exist_ok=True)

    inference_config = Path(__file__).resolve().parent / "inference-config-codex-sol.v1.json"
    inference_config_digest = compute_inference_config_digest(inference_config)

    # Verify OpenAI API is reachable
    print(f"Model: {OPENAI_MODEL}, reasoning_effort: {REASONING_EFFORT}")
    try:
        import urllib.request

        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        models = json.loads(resp.read())
        available = [
            m["id"] for m in models["data"] if "sol" in m["id"].lower() or "5.6" in m["id"]
        ]
        print(f"OpenAI reachable. Matching models: {available[:5]}")
    except Exception as exc:
        print(f"WARNING: OpenAI model check failed: {exc}")
        print("Proceeding anyway — will fail on first completion if unreachable.")

    all_results: list[AttemptResult] = []

    if args.smoke_test:
        attempts = [(DEV_PANEL[2], "proof", 0)]  # primepy proof
    else:
        attempts = [
            (repo, mode, idx)
            for repo in DEV_PANEL
            for mode in MODES
            for idx in range(ATTEMPTS_PER_REPO_MODE)
        ]

    if args.benchmark:
        attempts = [(r, m, i) for r, m, i in attempts if r["benchmark_id"] == args.benchmark]
    if args.mode:
        attempts = [(r, m, i) for r, m, i in attempts if m == args.mode]

    print(f"\nDevelopment screen: {len(attempts)} attempts")
    print(f"Docker image: {args.docker_image}")
    print(f"Probe root: {probe_root}\n")

    for i, (repo, mode, idx) in enumerate(attempts):
        print(f"\n[{i + 1}/{len(attempts)}]")
        result = run_one_attempt(
            vero_root=vero_root,
            vero_python=args.vero_python,
            docker_image=args.docker_image,
            benchmark_id=repo["benchmark_id"],
            benchmark_dir_name=repo["directory"],
            mode=mode,
            attempt_index=idx,
            probe_root=probe_root,
            api_key=api_key,
            inference_config_digest=inference_config_digest,
        )
        all_results.append(result)

        results_path = probe_root / "results.jsonl"
        with open(results_path, "a") as f:
            f.write(
                json.dumps(
                    {
                        "attempt_id": result.attempt_id,
                        "benchmark_id": result.benchmark_id,
                        "mode": result.mode,
                        "attempt_index": result.attempt_index,
                        "turns": result.turns,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "cached_input_tokens": result.cached_input_tokens,
                        "reasoning_output_tokens": result.reasoning_output_tokens,
                        "tool_calls": result.tool_calls,
                        "wall_seconds": round(result.wall_seconds, 2),
                        "stop_reason": result.stop_reason,
                        "infrastructure_errors": result.infrastructure_errors,
                        "integrity_errors": result.integrity_errors,
                        "scored": result.scored,
                        "materialization": result.materialization,
                        "grade": result.grade,
                    }
                )
                + "\n"
            )

    # Summary
    totals = summarize(all_results)
    print(f"\n{'=' * 60}")
    print("  SCREEN RESULTS")
    print(f"{'=' * 60}")
    print(
        f"  Scored attempts: {totals['scored_attempts']}/{totals['total_attempts']} "
        f"({totals['infrastructure_invalid_attempts']} infrastructure-invalid, excluded)"
    )
    print(f"  Total: {totals['total_passed_specs']}/{totals['total_specs']} specs passed")
    print(
        f"  Repos with nonzero strict coverage: {len(totals['repos_with_nonzero_coverage'])} "
        f"({', '.join(totals['repos_with_nonzero_coverage']) or 'none'})"
    )
    print(f"  Pooled strict success rate: {totals['pooled_strict_rate']}")
    print(f"\n  Screen {'PASSES' if totals['screen_pass'] else 'does not pass'}")

    summary = {
        "probe_id": f"vero-codex-sol-dev-screen-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
        "model": OPENAI_MODEL,
        "reasoning_effort": REASONING_EFFORT,
        "harness": f"anarres/vero-codex-sol-harness@{HARNESS_VERSION}",
        **totals,
    }

    summary_path = probe_root / "probe_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\n  Summary written to: {summary_path}")


if __name__ == "__main__":
    main()
