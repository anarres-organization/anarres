# Vulnerability-exploitation qualification

This study asks whether CyberGym can support a controlled comparison of
training environments for an agentic starting policy. The current
[v2 protocol](qualification-protocol.v2.json) defines CyberGym as both the
candidate training pool and the source of an isolated target, separated by the
[task-identity standard](DISJOINTNESS_AUDIT.md). It fixes the starting policy,
probe design, reliability gates, and abstention rule before downstream RL.
The [decision tree](DECISION_TREE.md) states the conditional path to a pilot.

## Current evidence and next gate

The frozen 48-task development probe passed oracle, no-op, and repeated-reset
checks after two fixtures were quarantined and replaced in frozen order.
[Fixture results](PROBE_FIXTURE_GATE.md) and
[containment results](CONTAINMENT_RESULTS.md) record the completed static gate.
A one-task [pipeline check](PHASE_C_PIPELINE_VALIDATED.md) exercised model
serving, agent tools, and grading end to end. It is a harness check, not a
measurement of the full candidate pool.

The next scientific gate is the frozen-policy probe: two independent
$G=8$ views of the 48 admitted tasks with the pinned starting model. It must
establish strict success, mixed-group support, measurement reliability,
infrastructure validity, and cost before a training pilot can be approved.
The [reliability analysis](POWER_ANALYSIS.md) and
[operating-characteristic simulation](reliability_oc.json) set this decision
in advance. No claim-bearing cyber RL result is recorded here.

## Development record

Earlier [CyberGym measurements](CYBER_QUALIFICATION_SUMMARY.md) showed that
the same model's observed exploit success changed with the agent scaffold.
Its repeated-rollout sweep also found sparse but nonzero reward variation.
These measurements were made with a different starting model and do not
substitute for the current protocol's warm-start probe. The
[v1 bakeoff](HISTORICAL_V1_BAKEOFF.md) and the
[earlier research plan](../HISTORICAL_VULNERABILITY_PLAN.md) remain available
as design records.

Formal-verification environments have a separate
[plan and source qualification path](../formal-verification/README.md). Their
proof-checker results are not pooled with exploit-verifier outcomes.
