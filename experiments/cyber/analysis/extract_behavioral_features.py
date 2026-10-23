#!/usr/bin/env python3
"""Extract behavioral proxy features from exploit harness trajectories.

Reads harness_results.json from each task workspace and the batch result
files to produce a feature matrix for utility prediction analysis.
"""

import json
import os
from collections import Counter


def extract_features(workspace_dir: str, batch_result: dict) -> dict:
    """Extract behavioral features from a single task's trajectory."""
    harness_path = os.path.join(workspace_dir, "harness_results.json")
    if not os.path.exists(harness_path):
        return None

    with open(harness_path) as f:
        harness = json.load(f)

    tool_calls = harness.get("tool_calls", [])
    submissions = harness.get("submissions", [])
    turns = harness.get("turns", 0)
    in_tok = harness.get("total_input_tokens", 0)
    out_tok = harness.get("total_output_tokens", 0)

    tool_dist = Counter(tc["tool"] for tc in tool_calls)
    n_read = tool_dist.get("read_file", 0)
    n_bash = tool_dist.get("bash", 0)
    n_write = tool_dist.get("write_file", 0)
    n_tools = len(tool_calls)

    # Submission features
    n_submissions = len(submissions)
    first_sub_turn = submissions[0]["turn"] if submissions else turns + 1
    submit_commands = [
        s
        for s in submissions
        if "submit.sh" in s.get("command", "") or "submit.sh" in str(s.get("result", ""))
    ]
    n_real_submissions = len(submit_commands)

    # Tool sequence features
    bash_commands = [tc["input"].get("command", "") for tc in tool_calls if tc["tool"] == "bash"]
    n_grep = sum(1 for c in bash_commands if "grep" in c)
    n_cat = sum(1 for c in bash_commands if c.strip().startswith("cat "))
    n_python = sum(1 for c in bash_commands if "python" in c)
    n_find = sum(1 for c in bash_commands if c.strip().startswith("find "))
    n_compile = sum(
        1 for c in bash_commands if any(k in c for k in ["gcc", "g++", "make", "cmake"])
    )
    n_hexdump = sum(1 for c in bash_commands if any(k in c for k in ["xxd", "hexdump", "od "]))

    # Read targets
    read_paths = [tc["input"].get("path", "") for tc in tool_calls if tc["tool"] == "read_file"]
    read_readme = any("README" in p or "readme" in p for p in read_paths)
    read_description = any("description" in p for p in read_paths)
    read_error = any("error" in p for p in read_paths)
    read_patch = any("patch" in p or "diff" in p for p in read_paths)
    read_source = any(p.endswith((".c", ".cc", ".cpp", ".h", ".hpp")) for p in read_paths)

    # Write features
    write_paths = [tc["input"].get("path", "") for tc in tool_calls if tc["tool"] == "write_file"]
    n_poc_writes = sum(
        1
        for p in write_paths
        if any(k in p.lower() for k in ["poc", "exploit", "crash", "fuzz", "input", "payload"])
    )
    n_script_writes = sum(1 for p in write_paths if p.endswith((".py", ".sh")))

    # Exploration vs exploitation ratio
    exploration_tools = n_read + n_grep + n_cat + n_find
    exploitation_tools = n_write + n_python + n_compile + n_hexdump + n_poc_writes
    total_categorized = exploration_tools + exploitation_tools
    exploit_ratio = exploitation_tools / max(total_categorized, 1)

    # Token efficiency
    tokens_per_turn = (in_tok + out_tok) / max(turns, 1)
    output_ratio = out_tok / max(in_tok, 1)

    # Submission result features
    any_exit1 = any("exit_code=1" in s.get("result", "") for s in submissions)
    any_exit0_submit = any(
        "exit_code=0" in s.get("result", "") and "submit.sh" in s.get("command", "")
        for s in submissions
    )

    return {
        "task_id": batch_result.get("task_id", ""),
        "project": batch_result.get("project", ""),
        "success": batch_result.get("success", False),
        # Scale features
        "turns": turns,
        "n_tool_calls": n_tools,
        "total_input_tokens": in_tok,
        "total_output_tokens": out_tok,
        "harness_time_s": batch_result.get("harness_time_s", 0),
        # Tool distribution
        "n_read_file": n_read,
        "n_bash": n_bash,
        "n_write_file": n_write,
        "n_submissions": n_submissions,
        "n_real_submissions": n_real_submissions,
        # Bash command types
        "n_grep": n_grep,
        "n_cat": n_cat,
        "n_python": n_python,
        "n_find": n_find,
        "n_compile": n_compile,
        "n_hexdump": n_hexdump,
        # Read targets
        "read_readme": read_readme,
        "read_description": read_description,
        "read_error": read_error,
        "read_patch": read_patch,
        "read_source": read_source,
        # Write features
        "n_poc_writes": n_poc_writes,
        "n_script_writes": n_script_writes,
        # Ratios
        "exploit_ratio": round(exploit_ratio, 4),
        "first_sub_turn": first_sub_turn,
        "tokens_per_turn": round(tokens_per_turn, 1),
        "output_ratio": round(output_ratio, 4),
        # Submission outcomes
        "any_exit1": any_exit1,
        "any_exit0_submit": any_exit0_submit,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--workspace-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    agg_path = os.path.join(args.results_dir, "_aggregate.json")
    with open(agg_path) as f:
        agg = json.load(f)

    features = []
    for result in agg["results"]:
        task_id = result["task_id"]
        task_num = task_id.split(":")[1]
        ws = os.path.join(args.workspace_dir, task_num)

        feat = extract_features(ws, result)
        if feat:
            features.append(feat)
            status = "OK" if feat["success"] else "  "
            tc = feat["n_tool_calls"]
            ns = feat["n_submissions"]
            er = feat["exploit_ratio"]
            print(f"  [{status}] {task_id:20s} tools={tc:2d} subs={ns} exploit_ratio={er:.2f}")
        else:
            print(f"  [??] {task_id:20s} no harness_results.json")

    with open(args.output, "w") as f:
        json.dump(features, f, indent=2)

    n_ok = sum(1 for f in features if f["success"])
    print(f"\nExtracted {len(features)} tasks, {n_ok} successes")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
