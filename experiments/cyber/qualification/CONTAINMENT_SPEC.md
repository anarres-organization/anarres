# CyberGym containment specification (Phase B)

Status: specification. No fixture has been materialized or executed. This maps
the protocol-v2 containment and fixture gates onto concrete, checkable controls
that must pass **before** any model-based measurement (frozen order, steps 5-6).

Scope: the frozen 48-task probe subset and, once materialized, the target panel.
All work is local-only and isolated; see the repository `SECURITY.md` and the
CyberGym submission/harness documentation for the authoritative upstream rules.

## Threat model (what must not happen)

- The agent reaches any network outside its isolated task network.
- The agent reads the fixed/patched build, the reference solution, expected
  flags, or grader credentials.
- A task leaks identity or artifacts into another task, the target panel, or the
  warm start.
- An infrastructure failure (sandbox, timeout, dependency, reset, grader) is
  recorded as a scientific reward of zero.
- The grader is reachable or readable by the agent.

## Required controls and how each is verified (no model running)

| Control | Requirement | Verification (static / dry-run) |
| --- | --- | --- |
| Network egress | Denied by default; only the isolated task network reachable | Inspect the container network policy and the firewall allowlist; attempt an outbound connection from a non-agent probe container and confirm failure |
| Submission service | Local-only; never bound to a public interface | Confirm bind address is loopback/task-net only; port scan from outside the task net returns closed |
| Fixed/patched build | Absent from the agent filesystem and env | Enumerate agent-visible mounts and image layers; assert the patched build path is not present |
| Reference solution / PoC | Absent from the agent filesystem | Grep the agent-visible tree for known solution artifact names; assert none |
| Secrets / flags / grader creds | Outside the agent sandbox | Scan agent env and mounts; assert no secret material; grader runs in a separate trust domain |
| Grader isolation | Grader not agent-readable or agent-reachable | Confirm grader lives outside the agent network and filesystem namespace |
| Action logging | Every reachable service and task-scoped action logged | Confirm the logging sink receives a dry-run action and records it immutably |
| Reset determinism | Repeated reset reproduces identical task state | Reset the same fixture twice; compare input digests (see fixture manifest) |

## Failure typing (integrity rule)

Every check failure is typed. Containment failures and infrastructure failures
(sandbox, timeout, dependency, reset, grader) are recorded separately and never
become scientific reward zero. This mirrors the four-state machine in
`packages/environments/src/anarres/environments/qualification.py`
(REPAIR / QUARANTINE / RESERVE / ADMITTED): an infra-invalid fixture is REPAIR,
an oracle failure or a passing no-op is QUARANTINE, and a zero-variance-but-valid
fixture is RESERVE — none of these is a scientific zero.

## Budget checkpoint

Building this containment from the current zero-sandbox state is bounded by the
frozen feasibility budget (5 engineering days, 7 elapsed days, 1 TiB retained).
If the build overruns, stop and report rather than consuming pilot budget
(`feasibility_budget.phase_b_containment_build_checkpoint` in protocol-v2).

## Exit criterion

Phase B is complete only when every control above passes for all admitted
fixtures (100% oracle pass, 100% no-op rejection, 100% repeated-reset agreement,
zero unresolved containment failures) and the results are recorded in the fixture
manifest. Only then may Phase C (the model-based floor probe) run.
