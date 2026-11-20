# Customer-support environment utility

**Status:** STATE-Bench source qualification complete; the starting policy,
candidate environments, learning operator, and outcome prediction are not yet
frozen.

This study asks whether measurements made before an agent-learning run can
predict which customer-support experience will improve held-out task completion
at a fixed learning and inference budget. The first source is the customer-
support domain in [STATE-Bench](https://github.com/microsoft/STATE-Bench), whose
Agent Learning Track provides 100 training trajectories, 50 held-out tasks, a
locked simulator and judge, and five repeated evaluations per task.

The first experiment uses the benchmark's native learning interface. Candidate
environments will be matched subsets or mixtures of the released training
experience. Each candidate will feed the same learning operator, retrieval
limit, starting agent, and held-out evaluation contract. This tests environment
selection inside a closed learning loop. It does not establish that the same
measurements predict parameter-updating post-training.

## Research decision

The planned decision is:

> Given one starting agent and a fixed learning budget, which candidate
> distribution of customer-support experience produces the greatest held-out
> task improvement without increasing important task-level regressions?

The study will compare a policy-relative selector with simple alternatives
under the same candidate size and cost accounting. Required baselines include
source-proportional sampling, deterministic random sampling, and a static
difficulty rule. Candidate definitions may change during development, before
the protocol is frozen. Once the freeze occurs, candidate membership,
prediction, abstention rule, and evaluation remain unchanged.

## Evidence layers

The work proceeds through four separate gates:

1. **Source qualification.** Verify the pinned benchmark revision, license,
   task inventory, train/test split, released trajectories, and locked protocol
   files without running a model or reading evaluation outcomes.
2. **Starting-agent measurement.** Run repeated probes on development
   experience and record task completion, valid execution, cost, output tokens,
   tool use, and task-level outcome variation. Infrastructure-invalid attempts
   remain separate from task failures.
3. **Prospective learning test.** Freeze candidate environments and their
   predicted ordering before building any candidate-specific learning artifact.
   Evaluate every candidate on the same 50-task test split with five runs per
   task.
4. **External and post-training tests.** Test the selector on an independently
   constructed source such as
   [tau2-bench](https://github.com/sierra-research/tau2-bench). A separate
   protocol will be required before making claims about gradient-based
   post-training or voice agents.

## Outcomes and boundaries

The primary outcome is held-out task-completion pass@1 relative to the same
agent without the candidate learning artifact. Secondary outcomes are pass^5,
user-experience score, cost per task, pairwise candidate ordering, allocation
regret, and task-level regressions. The exact regression threshold and
uncertainty rule remain unresolved before freeze.

The benchmark uses synthetic customer-support workflows. A successful result
would support prediction within this source, agent, learning operator, and
budget. It would not establish transfer to private workflows, other agent
families, voice interaction, or parameter-updating training.

## Reproduce source qualification

Validate the public source registry, protocol, and saved qualification record:

```bash
python scripts/audit_sources.py
```

With the pinned STATE-Bench checkout available, reproduce the native source
audit without running a model or opening result directories:

```bash
python scripts/audit_state_bench.py /path/to/STATE-Bench
```

The checkout must be at commit
`5644b1838d96bc4483da29642d058ecaa6f80f7f`. The audit verifies the exact
customer-support inventories, split membership, released training trajectories,
protocol hashes, and MIT license. [`PROTOCOL.json`](PROTOCOL.json) records the
gates that remain before a prospective freeze.

After a starting agent has been chosen and repeated training-side runs are
available, measure them without reading the held-out split:

```bash
python scripts/measure_starting_agent.py \
  /path/to/STATE-Bench \
  /path/to/customer-support-train-runs \
  --num-runs 5 \
  --output starting-agent-measurement.json
```

The measurement keeps missing, malformed, and unscored attempts separate from
scientific task failures. Completion-signal density is reported only when
output-token accounting is complete. The converter reads final trajectory files;
the frozen runner must separately retain transient retry attempts and their
costs. This training-side probe is an Anarres research extension rather than an
official Agent Learning Track submission. Its records remain development
evidence and cannot contain candidate-specific held-out outcomes.

