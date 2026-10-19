# Conditional decision tree (not a signed go/no-go)

This is intentionally conditional. A signed go/no-go for RL is possible only
after Phase C runs on a Phase-B-qualified harness. Nothing here authorizes RL.

```text
PHASE A  (desk, no GPU)  -- protocol-v2 frozen, this directory
  |
  |-- Verify warm-start artifact exists locally and matches the agentic
  |   Nemotron-8B (record digest).            --> if mismatch/absent: STOP, resolve warm start
  |
  |-- Report distinct-project and distinct-patch-class counts for CyberGym
  |   under the disjointness standard.
  |       capacity: >= 246 target tasks from disjoint projects AND
  |                 training pool able to yield 4-6 distinct environments?
  |         no  --> CyberGym cannot be both source and target at this
  |                 granularity: reconsider target (e.g. external-only) or
  |                 relax environment count with justification. STOP for review.
  |         yes --> continue
  v
PHASE B  (Docker, no GPU)  -- frozen-order steps 5-6
  |
  |-- Materialize frozen 48-task probe subset + >= 246 target partition
  |   from one salted ordering (mutually exclusive, probe excluded from target).
  |-- Build containment; run oracle / no-op / repeated-reset on the 48 fixtures.
  |       all static_fixture_gates pass (oracle 1.0, no-op 1.0, reset 1.0,
  |       no egress, grader+fixed-build hidden, secrets scrubbed)?
  |         no  --> fixtures/containment not qualified: fix or STOP.
  |         budget overrun checkpoint hit? --> STOP and report.
  |         yes --> continue
  v
PHASE C  (needs model + Phase B pass)  -- frozen warm_start_probe
  |
  |-- Nemotron-8B, G=16 as two independent G=8 views, 48 tasks.
  |   Compute strict success, rho, H, mixed-group fraction, two-view agreement.
  |
  |-- Consult reliability_oc.json for the observed success regime:
  |       regime below reliably-measurable floor (per-task success < ~0.30)?
  |         yes --> increase rollouts within budget, else return UNMEASURABLE.
  |         no  --> evaluate gates:
  |
  |       strict success in [0.05, 0.80] AND >= 8 mixed valid groups (>= 20%)
  |       AND reliability gates agree AND infra-failure <= 5%?
  |         yes --> PROCEED to frozen qualification and pilot design
  |         no, success < 0.05 (floor) --> CyberGym becomes EXTERNAL-TARGET-ONLY;
  |                 reconsider in-domain training source. (A hard target is still
  |                 scientifically valid as an endpoint.)
  |         no, success > 0.80 (saturated) --> not an informative training regime.
  v
(only after a PROCEED) --> pilot contract freeze --> matched-budget 2-seed pilot
```

## Outputs each phase must preserve

- Phase A: `qualification-protocol.v2.json`, this rationale, the frozen OC
  simulation, warm-start digest, capacity report.
- Phase B: content hashes of the probe subset and target partition, containment
  specification, oracle/no-op/reset manifests, contamination/identity audit.
- Phase C: warm-start measurement summary (strict success, rho, H, mixed,
  reliability agreement, infra-failure), and one of the three decision outcomes.
