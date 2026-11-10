# Vulnerability-exploitation qualification

This study asks whether CyberGym can support a controlled comparison of
training environments for an agentic starting policy. The
[v2 protocol](qualification-protocol.v2.json) defines task identity,
containment, reliability gates, and the abstention rule that governed the
initial qualification campaign. The later matched-scaffold study shows why the
agent interface belongs to the measured environment rather than benchmark
metadata alone.

## Released evidence

The frozen 48-task development set passed oracle, no-op, repeated-reset, and
containment checks after two fixtures were replaced in frozen order.
[Fixture results](PROBE_FIXTURE_GATE.md) and
[containment results](CONTAINMENT_RESULTS.md) preserve those gates.

OpenHands floor probes produced no verified exploits for Nemotron-Terminal-8B
or Feyospace. A matched Feyospace scaffold then completed 6 of 50 single-attempt
tasks. On a separate eight-attempt sweep, 13 of 50 tasks produced mixed
outcomes. The [development summary](CYBER_QUALIFICATION_SUMMARY.md) reports the
scaffold comparison, repeated-policy measurements, uncertainty, and compute.
These results establish policy-relative signal under one model and scaffold.
They do not compare training environments or measure downstream RL utility.

## Development record

The [v1 bakeoff](HISTORICAL_V1_BAKEOFF.md), the original
[decision tree](DECISION_TREE.md), and the
[earlier research plan](../HISTORICAL_VULNERABILITY_PLAN.md) remain design
records rather than current execution instructions. A future controlled
training comparison requires a new frozen contract tied to its exact model,
scaffold, candidate environments, target, and budget.

Formal-verification environments have a separate
[plan and source qualification path](../formal-verification/README.md). Their
proof-checker results are not pooled with exploit-verifier outcomes.
