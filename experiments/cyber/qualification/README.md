# Vulnerability-exploitation qualification

This study asks whether CyberGym can support a controlled comparison of
training environments for an agentic starting policy. The
[v2 protocol](qualification-protocol.v2.json) defines task identity,
containment, reliability gates, and the abstention rule that governed the
initial qualification campaign. The later matched-scaffold study shows why the
agent interface belongs to the measured environment rather than benchmark
metadata alone. Here, a **scaffold** is the agent harness, tools, prompts, and
interaction interface wrapped around the model.

## Start here

Install the vulnerability adapter, connect a sanitized CyberGym panel, and run
source qualification:

```bash
uv tool install ./packages/vulnerability
anarres vulnerability status
anarres init ./candidate-panel \
  --adapter vulnerability \
  --revision <immutable-revision> \
  --license <usage-terms>
anarres inspect ./candidate-panel
anarres qualify ./candidate-panel
```

Qualification checks the pinned panel, containment records, and verifier
fixtures. Model execution is not available through this adapter yet.

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

## Grouping and selection

`selection_law.py` states two exact results. Grouping has no hidden upside:
expected advantage mass is 2Gp(1 - p), so per-rollout mass is 2p(1 - p) for every
group size, and discarding groups whose rollouts all agree costs exactly 1 over
coverage, which is 4.03 times at 0.035 and G = 8. Screening has a hidden
downside: choosing the best of ten identical environments at 400 rollouts per
arm reports 1.40 times the true density. The script gives a two-regime rule that
certifies a champion under one percent bias, or reports the panel as
homogeneous; the null panel lands at 1.06 times truth with a 5.0 percent claim
rate, and a real 2.3 times leader at 1.00 times with a 94.2 percent claim rate.
See [SELECTION_LAW.md](SELECTION_LAW.md).

## Screening budget

`screening_budget.py` computes the exact probability that a screening round
names the right environment, then asks whether the same budget works better
spread evenly or split into a pilot and a deeper pass. At 400 rollouts per arm
and ten candidates a 2.3 times leader is identified 0.994 of the time, a 1.5
times leader 0.664, and a 1.2 times leader 0.334. Reallocating that budget, half
to a pilot and the rest to the top four, lifts the 1.5 times case to 0.742,
equivalent to an even split with 536 rollouts per arm.
See [SCREENING_BUDGET.md](SCREENING_BUDGET.md).

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
