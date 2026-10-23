#!/usr/bin/env python3
"""G-rollout batch runner for ρ/H measurement.

Runs G independent rollouts per task to compute per-group advantage mass,
usable signal density (ρ), and effective coverage (H) as defined in
the ICLR paper Eq. 5-6.

Resume-safe: rollout results are saved as {task_num}_r{rollout_id}.json.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time


def generate_task(task_id, out_dir, data_dir, server_url, cybergym_dir, mask_map):
    cmd = [
        sys.executable,
        "-m",
        "cybergym.task.gen_task",
        "--task-id",
        task_id,
        "--out-dir",
        out_dir,
        "--data-dir",
        data_dir,
        "--server",
        server_url,
        "--difficulty",
        "level3",
    ]
    if mask_map:
        cmd.extend(["--mask-map", mask_map])
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(cybergym_dir, "src")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cybergym_dir,
        env=env,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Task gen failed for {task_id}: {result.stderr[:500]}")
    return out_dir


def run_exploit_harness(work_dir, harness_path, api_url):
    env = os.environ.copy()
    env["API_URL"] = api_url
    result = subprocess.run(
        [sys.executable, harness_path, work_dir],
        capture_output=True,
        text=True,
        timeout=1800,
        env=env,
    )
    return result.stdout, result.stderr, result.returncode


def check_submission_success(work_dir):
    results_path = os.path.join(work_dir, "harness_results.json")
    if not os.path.exists(results_path):
        return {"submitted": False, "success": False, "submissions": []}

    with open(results_path) as f:
        results = json.load(f)

    submissions = results.get("submissions", [])
    success = any("exit_code=1" in sub.get("result", "") for sub in submissions)
    return {
        "submitted": len(submissions) > 0,
        "success": success,
        "submissions": submissions,
        "turns": results.get("turns", 0),
        "total_input_tokens": results.get("total_input_tokens", 0),
        "total_output_tokens": results.get("total_output_tokens", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="G-rollout batch runner for rho/H measurement")
    parser.add_argument("--panel", required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--cybergym-dir", required=True)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--server-url", default="http://127.0.0.1:8666")
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:30000/v1/chat/completions",
    )
    parser.add_argument("--mask-map", default=None)
    parser.add_argument("--workspace-dir", default="/tmp/cyber_g8_workspaces")
    parser.add_argument("--G", type=int, default=8, help="Rollouts per task")
    parser.add_argument(
        "--start-task",
        type=int,
        default=0,
        help="Index to start from in panel",
    )
    args = parser.parse_args()

    with open(args.panel) as f:
        panel = json.load(f)

    os.makedirs(args.results_dir, exist_ok=True)
    os.makedirs(args.workspace_dir, exist_ok=True)

    G = args.G
    total_rollouts = len(panel) * G
    done = 0
    successes = 0

    print(f"=== G={G} rollout sweep: {len(panel)} tasks × {G} = {total_rollouts} rollouts ===")
    print(f"Results dir: {args.results_dir}")

    for i, task in enumerate(panel):
        if i < args.start_task:
            continue

        task_id = task["task_id"]
        task_num = task_id.split(":")[1]

        for r in range(G):
            result_file = os.path.join(args.results_dir, f"{task_num}_r{r}.json")

            if os.path.exists(result_file):
                with open(result_file) as f:
                    existing = json.load(f)
                done += 1
                if existing.get("success"):
                    successes += 1
                continue

            print(f"\n[task {i + 1}/{len(panel)}, rollout {r + 1}/{G}] {task_id}")

            work_dir = os.path.join(args.workspace_dir, f"{task_num}_r{r}")
            task_result = {
                "task_id": task_id,
                "project": task.get("project", ""),
                "rollout_id": r,
                "G": G,
            }

            try:
                if os.path.exists(work_dir):
                    shutil.rmtree(work_dir)
                os.makedirs(work_dir)

                t0 = time.time()
                generate_task(
                    task_id,
                    work_dir,
                    args.data_dir,
                    args.server_url,
                    args.cybergym_dir,
                    args.mask_map,
                )
                gen_time = time.time() - t0

                t1 = time.time()
                stdout, stderr, returncode = run_exploit_harness(
                    work_dir, args.harness, args.api_url
                )
                harness_time = time.time() - t1

                outcome = check_submission_success(work_dir)
                task_result.update(
                    {
                        "success": outcome["success"],
                        "submitted": outcome["submitted"],
                        "turns": outcome.get("turns", 0),
                        "total_input_tokens": outcome.get("total_input_tokens", 0),
                        "total_output_tokens": outcome.get("total_output_tokens", 0),
                        "n_submissions": len(outcome.get("submissions", [])),
                        "harness_time_s": round(harness_time, 1),
                        "gen_time_s": round(gen_time, 1),
                    }
                )

                status = "OK" if outcome["success"] else "  "
                done += 1
                if outcome["success"]:
                    successes += 1
                rate = successes / max(done, 1)
                print(f"  [{status}] {harness_time:.0f}s, running {successes}/{done} = {rate:.1%}")

            except Exception as e:
                task_result["success"] = False
                task_result["error"] = str(e)[:500]
                done += 1
                print(f"  ERROR: {e}")

            with open(result_file, "w") as f:
                json.dump(task_result, f, indent=2, default=str)

        # After all G rollouts for this task, print group summary
        group_successes = 0
        for r in range(G):
            rf = os.path.join(args.results_dir, f"{task_num}_r{r}.json")
            if os.path.exists(rf):
                with open(rf) as f:
                    rd = json.load(f)
                if rd.get("success"):
                    group_successes += 1
        print(
            f"  Group {task_id}: {group_successes}/{G} successes "
            f"(A_raw = {2 * group_successes * (G - group_successes) / (G - 1):.2f})"
        )

    print(f"\n=== SWEEP COMPLETE: {done} rollouts, {successes} successes ===")
    print(f"Overall rate: {successes}/{done} = {successes / max(done, 1):.1%}")


if __name__ == "__main__":
    main()
