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

## Rollout budget law

The [budget law](SIGNAL_BUDGET_LAW.md) derives what a fixed rollout budget buys,
exactly and without simulation. Expected advantage mass carries no finite-G
bias, coverage is 1 - p^G - (1 - p)^G, and the budget-normalized variance is
nearly flat in G at sparse success rates while falling as 1/G at dense ones.
`signal_budget_theory.py` rebuilds the released H and coverage from the
published k vector and checks every identity against a seeded simulation. The
same algebra shows verifier false negatives act as a contraction toward one
half, so a bad verifier hides 37 percent of the signal at p = 0.035 and reports
33 percent more at p = 0.75.

## Signal-density comparison

The [comparison note](SIGNAL_DENSITY_COMPARISON.md) turns environment selection
into a testable claim. Density is symmetric in p, so a comparison must test
equality of p (1 - p) rather than equality of success rate; `environment_ranking.py`
profiles the binomial likelihood over the common density and over which side of
one half each environment sits. At 400 rollouts per arm its minimum detectable
ratio is 0.15 to 2.30 times the baseline, and a verifier with 38 percent false
negatives reports a 4.2 times density difference between a 0.10 and a 0.90
environment that carries none.

## Paired comparison design

`paired_design.py` decomposes the variance of a density difference into the
binomial part and the part that comes from two panels inheriting different task
mixes. At the published panel the mix term is the larger of the two, 5.91
against 5.17, so a paired comparison on shared tasks cuts the difference
standard deviation from 11.11 to 7.32. See [PAIRED_DESIGN.md](PAIRED_DESIGN.md).

The practical rule is to run both environments on the same panel. When that is
impossible, report the panel overlap, because disjoint panels at 400 rollouts per
arm cannot separate densities closer than 2.3 times.

## Early stopping

`sequential_design.py` evaluates a three-look design exactly by dynamic
programming over the joint success lattice, with a closed-form profile
likelihood ratio. At the fixed protocol's minimum detectable ratio the design
keeps its power, 0.861 against 0.864, and spends 310 rollouts per arm instead of
400; under the null it spends 363. See [SEQUENTIAL_DESIGN.md](SEQUENTIAL_DESIGN.md).

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

## Released evidence record

`cybergym_released_evidence.json` states what this workstream has released and
where it stops. It pins the policy, scaffold, 50-task panel, verifier contract,
and cost unit, hashes both floor-probe statistics files, and sets
`task_level.released` to `false` because the 400 per-rollout JSONs stayed on the
cluster. The published rho, H, and k values appear with
`recomputed_from_rows: false` so no reader can mistake them for a recomputation.

```bash
anarres-vulnerability status --evidence experiments/cyber/qualification/cybergym_released_evidence.json
anarres-vulnerability verify --evidence experiments/cyber/qualification/cybergym_released_evidence.json
anarres-vulnerability profile --evidence experiments/cyber/qualification/cybergym_released_evidence.json
```

`verify` recomputes the floor-probe counts from their per-task rows and fails on
digest drift, count mismatch, pooled scaffolds, or a claim that aggregates came
from rows. `profile` refuses to export an environment-profile input while task
rows stay unreleased. The floor probes keep their OpenHands scaffold as a
separate contract from the custom harness that produced the 50-task sweep.
