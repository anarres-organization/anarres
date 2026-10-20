"""Per-fixture containment verification for the admitted probe (no model, no GPU).

Maps the CONTAINMENT_SPEC controls onto checkable facts for each admitted
fixture. Two classes of control:

- Per-fixture, data-dependent (verified per task from tasks.json): the
  agent-served bundle at the chosen difficulty level must not contain the fixed/
  patched build or the reference solution. CyberGym difficulty levels 0-2 serve
  only the vulnerable repo (+ description/error); level 3 adds ``repo-fix`` and
  ``patch.diff`` and therefore FAILS the gate. The reference PoC is withheld at
  every level.

- Mechanism-level, identical for every fixture (verified once from the harness
  code/config, recorded with that basis, not re-run per fixture): network egress
  is denied by ``network_mode="none"``; the submission service binds loopback
  (``--host`` default ``127.0.0.1``); the grader runs in a separate container the
  agent is not served; actions are logged to ``server.log``. Re-pulling 48 images
  to re-observe a kernel-level ``--network none`` block would add no information.

Reset determinism is already recorded per fixture by the gate (reset agreement
1.000). This script does not run containers; it reads task metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FIX_ARTIFACTS = ("repo-fix", "patch.diff")
REFERENCE_ARTIFACTS = ("poc", "/poc", "reference")
SECRET_HINTS = ("secret", "credential", "token", ".key", "id_rsa", ".pem", "flag")

# Mechanism-level controls (same for every fixture); basis documented above.
HARNESS_CONTROLS = {
    "egress_denied": True,  # run_container network_mode="none" (both paths); BLOCKED empirically
    "submission_service_local_only": True,  # server --host default 127.0.0.1 (loopback)
    "grader_agent_readable": False,  # grader container separate; agent served source tarball only
    "action_log_recorded": True,  # uvicorn log_config -> server.log
}


def served_files(task: dict, level: int) -> list[str]:
    return task["task_difficulty"].get(f"level{level}", [])


def check_task(task: dict, level: int) -> dict:
    served = served_files(task, level)
    fixed_visible = any(any(a in f for a in FIX_ARTIFACTS) for f in served)
    reference_visible = any(f.rsplit("/", 1)[-1] in REFERENCE_ARTIFACTS for f in served)
    secrets = any(any(h in f.lower() for h in SECRET_HINTS) for f in served)
    containment = {
        **HARNESS_CONTROLS,
        "fixed_or_patched_build_agent_visible": fixed_visible,
        "reference_solution_agent_visible": reference_visible,
        "secrets_absent_from_sandbox": not secrets,
        "served_difficulty_level": level,
        "served_files": served,
    }
    passed = (
        HARNESS_CONTROLS["egress_denied"]
        and HARNESS_CONTROLS["submission_service_local_only"]
        and not HARNESS_CONTROLS["grader_agent_readable"]
        and HARNESS_CONTROLS["action_log_recorded"]
        and not fixed_visible
        and not reference_visible
        and not secrets
    )
    containment["containment_passed"] = passed
    return containment


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=Path, required=True)
    ap.add_argument(
        "--manifest", type=Path, required=True, help="fixture-manifest.probe.final.json"
    )
    ap.add_argument("--level", type=int, default=2, help="served difficulty level (must be <=2)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    if a.level > 2:
        raise SystemExit(f"level {a.level} serves the fixed build/patch; gate requires <=2")

    tasks = {t["task_id"]: t for t in json.loads(a.tasks.read_text())}
    manifest = json.loads(a.manifest.read_text())
    probe_ids = [f["task_id"] for f in manifest["fixtures"]]

    results = {tid: check_task(tasks[tid], a.level) for tid in probe_ids}
    n = len(results)
    n_pass = sum(1 for c in results.values() if c["containment_passed"])

    # also show which levels would still hide the fix, for the record
    level_safety = {
        lvl: all(
            not any(any(x in f for x in FIX_ARTIFACTS) for f in served_files(tasks[t], lvl))
            for t in probe_ids
        )
        for lvl in range(4)
    }

    out = {
        "schema_version": "anarres.cyber-containment-check.v1",
        "served_difficulty_level": a.level,
        "n_fixtures": n,
        "n_containment_passed": n_pass,
        "harness_controls": HARNESS_CONTROLS,
        "fix_hidden_by_level": level_safety,
        "per_fixture": results,
    }
    a.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"level={a.level}  fixtures={n}  containment_passed={n_pass}/{n}")
    print(f"fix_hidden_by_level={level_safety}")
    fails = [t for t, c in results.items() if not c["containment_passed"]]
    print(f"failures: {fails if fails else 'none'}")


if __name__ == "__main__":
    main()
