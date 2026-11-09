# Prospective environment selection for finance operations

**Status:** source qualification complete; policy, candidate bank, and outcome
contract are not yet frozen.

This study will test whether policy-relative measurements can choose among
finance training distributions before trained-policy outcomes are available.
The first generator-qualified task family is stateful accounting operations
with executable checks and explicit control policies. Reconciliation and
post-trade exception handling are the primary domain target, but their public
construction source remains under qualification.

## Qualified construction source

[Business Bench](https://github.com/erphq/business-bench) is pinned at commit
`0d09882b59a16f190feac09abc9331a733a6f96b`. At that revision, the repository
contains 187 generated desk-task families, including 36 labelled bookkeeping,
and nine stateful process-task families.

Four process workflows passed the upstream strict validator across seeds 0--4:

- freight accrual revision
- month-end close
- payment run
- payment-run need-to-know.

Each validation requires two successful and state-identical oracle runs, a
failing null agent, the intended failures from every declared negative
control, complete turn records, valid handbook citations, and a reproducible
policy handbook. All 20 workflow-by-seed checks passed. The machine-readable
record is in [`PREFLIGHT.json`](PREFLIGHT.json).

The preflight establishes generator validity for these seeds. It does not
qualify a starting model, define the final candidate mixtures, or reveal any
training outcome.

The [starting-policy qualification plan](STARTING_POLICY_QUALIFICATION.md)
defines the next gate. It begins with a pinned Qwen3-8B checkpoint on 128 new
development episodes and escalates only when the smaller policy produces
invalid tool use or insufficient reward variation.

## Prospective decision

The planned decision is:

> Given one starting policy and a fixed training budget, which finance-task
> distribution produces the greatest held-out executable improvement without
> violating material controls?

The panel will compare at least four matched candidates:

- a source-proportional mixture
- a size-matched static-difficulty mixture
- a policy-relative usable-signal mixture
- a policy-relative mixture with an explicit workflow-coverage constraint.

Candidate definitions may be revised during preflight, before the protocol is
frozen. Once training begins, candidate membership, prediction, abstention rule,
budgets, and evaluation remain unchanged.

The starting policy will be chosen on development scenarios only. A qualifying
policy must complete the tool protocol reliably and produce enough non-degenerate
task outcomes to measure candidate differences. Hosted frontier-agent results
do not substitute for this check because the claim-bearing policy must be open
to matched post-training.

## Partition and outcome lock

Development seeds validate generators and instrumentation. Candidate seeds are
disjoint and provide starting-policy measurements. Held-out scenario seeds and
content commitments are created before training, remain inaccessible to
candidate construction, and are opened only after every required arm and seed
passes the completeness gate.

`scripts/commit_panel.py` creates a salted SHA-256 commitment from a private
partition file. Its public record contains the source revision and partition
counts without exposing scenario seeds. The private file is revealed only
after the outcome gate opens, allowing the published commitment to be checked.

The study will report:

- executable task completion on held-out scenarios
- allocation regret and pairwise candidate ordering
- ledger and subledger consistency
- approval, bank-detail, and held-invoice control violations
- evidence provenance and cross-artifact consistency
- generated tokens, tool calls, wall time, and measurement cost
- training-seed variation and abstention when margins are too small.

Infrastructure failures remain separate from financial errors. A control
violation remains visible even when the task's aggregate score improves.

## External checks

The source registry separates construction sources from external evaluations.
BankerToolBench and FrontierFinance cover investment-research and artifact
workflows. The SecondState Finance Agent Benchmark provides a synthetic data
room and released tool traces. Accounted Bench provides open accounting tasks.
Vals Finance Agent Benchmark and Ramp Accounting Bench provide useful external
design targets, but their complete held-out task sets are not public
construction sources.

These sources will test transfer only after their licenses, task identities,
and evaluation contracts pass the relevant gate. Native outcomes remain
separate across accounting operations, research, and artifact production.

FINOS Common Domain Model is being audited as a representation layer for a
future post-trade panel. RecBench is a relevant reconciliation dataset, but its
public snapshot does not include the generator and evaluator described by its
dataset card. Neither source is admitted to prospective construction yet.

## Reproduce the source audit

Validate the public registry and preflight record:

```bash
python scripts/audit_sources.py
```

With the pinned Business Bench checkout available, verify its inventory and
the qualified workflow identities without reading result directories:

```bash
python scripts/audit_business_bench.py /path/to/business-bench
```

Create and later verify a sealed partition commitment:

```bash
python scripts/commit_panel.py commit private-panel.json > panel-commitment.json
python scripts/commit_panel.py verify private-panel.json panel-commitment.json
```

[`PROTOCOL.json`](PROTOCOL.json) records the preflight contract and the gates
that must be resolved before a prospective freeze.
