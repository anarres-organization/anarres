# Containment results (probe, 48 admitted fixtures)

Per-fixture verification of the CONTAINMENT_SPEC controls on the final 48-task
probe, with no model and no GPU. Together with the oracle/no-op/reset gate
(PROBE_FIXTURE_GATE.md) this closes the Phase-B static exit criterion. It is not
a model measurement; `execution_authorized` stays `false`.

## How each control was verified

Two classes of control, verified without running the agent:

**Per-fixture, data-dependent** — read from `tasks.json` per task, at the served
difficulty level:

- *Fixed/patched build not agent-visible* and *reference solution not
  agent-visible*: the agent is served the task bundle (the vulnerable repo, plus
  description/error at higher levels), not the grading image. CyberGym difficulty
  levels 0–2 serve only the vulnerable repo; **level 3 adds `repo-fix` and
  `patch.diff` and so fails the gate**. The reference PoC is withheld at every
  level. Verified per task at **level 2** (the most context that still hides the
  fix).

**Mechanism-level, identical for every fixture** — verified once from the harness
code/config and recorded with that basis (not re-run per fixture, since the
mechanism is image-independent):

- *Network egress denied*: `run_container` uses `network_mode="none"` on both
  grading paths (`server_utils.py`), and an outbound connection from inside a
  `--network none` task container was empirically BLOCKED (HARNESS_VALIDATION.md).
  Re-pulling 48 images to re-observe a kernel-level block would add no
  information.
- *Submission service local-only*: the server binds `--host` default
  `127.0.0.1` (loopback).
- *Grader not agent-readable*: the grader runs in a separate container; the agent
  is served only the source bundle.
- *Action logging*: the server writes an immutable `server.log` via its log
  config.

Reset determinism was already recorded per fixture by the gate (agreement 1.000).

## Result

| quantity | value |
| --- | ---: |
| fixtures checked | 48 |
| containment passed | **48 / 48** |
| fix hidden at level 0 / 1 / 2 / 3 | yes / yes / yes / **no** |
| served difficulty level used | 2 |
| failures | none |

| artifact | sha256 |
| --- | --- |
| `containment-report.probe.json` | `7fcf613a18a4a86a140c11e2fa8e6514ad844f6218cf3ac93f1e911f725df8df` |

All 48 admitted fixtures pass every containment control at difficulty level 2.
**Level 3 must not be served** — it exposes the fixed build and patch to the
agent and fails `fixed_or_patched_build_agent_visible: false`.

## Phase-B static exit criterion — met

| gate | required | measured |
| --- | --- | --- |
| oracle pass rate | 1.0 | 1.000 (48/48) |
| no-op rejection rate | 1.0 | 1.000 |
| repeated-reset agreement | 1.0 | 1.000 |
| unresolved containment failures | 0 | 0 |
| infrastructure failure fraction | ≤ 0.05 | 0.000 |

Phase B is complete for the probe. The only remaining step before Phase C is
operational: a free GPU to serve the warm start for the two-view floor probe.
Nothing here authorizes RL; Phase C emits one of proceed / external-target-only /
unmeasurable per DECISION_TREE.md.
