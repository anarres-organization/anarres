# Customer-support environment utility

**Status:** STATE-Bench source qualification complete; the starting agent,
candidate panel, learning operator, and selection prediction are not yet frozen.

This study asks whether measurements made before an agent-learning run can
predict which customer-support experience will improve held-out task completion
under a common learning and evaluation contract. The first source is the
customer-support domain in [STATE-Bench](https://github.com/microsoft/STATE-Bench), whose
Agent Learning Track provides 100 training trajectories, 50 held-out tasks, a
locked simulator and judge, and five repeated evaluations per task.

The first experiment uses the benchmark's native learning interface. Candidate
environments will be matched subsets of the released training
experience. Each candidate will feed the same learning operator, retrieval
limit, starting agent, and held-out evaluation contract. This tests environment
selection inside a closed learning loop. It does not establish that the same
measurements predict parameter-updating post-training.

## Research decision

The planned decision is:

> Given one starting agent and a fixed candidate size, which distribution of
> customer-support experience produces the greatest held-out task improvement
> without increasing important task-level regressions?

The study will compare a policy-relative selector with simple alternatives at
the same candidate size, with learning and inference costs reported separately.
The source-proportional, static-difficulty, and policy-relative candidates use
the same task-family quotas. A global deterministic-random candidate tests the
effect of leaving those quotas unconstrained. Candidate definitions may change
during development, before the protocol is frozen. Once the freeze occurs,
candidate membership, prediction, and evaluation remain unchanged.

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
regret, and task-level regressions. Allocation regret includes the no-learning
option, so a candidate receives no credit merely for being the least harmful
way to train. The checked-in scoring contract fixes a
descriptive regression threshold and task-stratified bootstrap before any
held-out outcome is observed. The starting agent, learning operator, and
run contract remain unresolved until the prospective freeze.

The benchmark uses synthetic customer-support workflows. A successful result
would support prediction within this source, agent, learning operator, and cost
profile. It would not establish transfer to private workflows, other agent
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
scientific task failures. Completion-signal density measures within-task outcome
variation per output token and is reported only when token accounting is
complete. The converter reads final trajectory files;
the frozen runner must separately retain transient retry attempts and their
costs. This training-side probe is an Anarres research extension rather than an
official Agent Learning Track submission. Its records remain development
evidence and cannot contain candidate-specific held-out outcomes.

## Qualify the execution route

The checked-in learning operator is a deterministic episodic-memory baseline.
It compacts each selected training trajectory into the user requests, ordered
domain-tool names, and assistant responses, then retrieves three records with
BM25. It uses only the released training trajectories and does not read held-out
task definitions, environments, or outcomes. [`LEARNING_OPERATOR.json`](LEARNING_OPERATOR.json)
records the exact contract.

First run the model-free operator smoke test against the pinned checkout:

```bash
python scripts/smoke_learning_operator.py \
  --checkout /path/to/STATE-Bench \
  --artifact-output /tmp/customer-support-smoke-learning.json \
  --output /tmp/customer-support-operator-smoke.json
```

[`SMOKE_PLAN.json`](SMOKE_PLAN.json) fixes one training task from each of the
eight customer-support task families. The smoke test verifies source identity,
train-only membership, deterministic artifact construction, and retrieval. It
makes no model calls and produces no scientific outcome.

Install the versioned extension into the qualified STATE-Bench checkout and
check whether the locked evaluator and starting-agent routes are configured:

```bash
python scripts/prepare_state_bench_extension.py \
  --checkout /path/to/STATE-Bench \
  --output /tmp/customer-support-extension.json

python scripts/preflight_execution.py \
  --checkout /path/to/STATE-Bench \
  --output /tmp/customer-support-preflight.json \
  --agent-model-name <reported-model-name> \
  --agent-provider <azure_openai-or-openai>
```

The preflight prints only whether required fields are present; it never prints
credential values. A scientific run remains blocked until the protocol-locked
GPT-5.4 simulator and judge route and one starting-agent route are both ready.
Once they are configured, run the eight train-side smoke tasks twice with
`AnarresEpisodicMemoryAgent`, no learning artifact, retrieval top-k 3, and one
retry attempt. This establishes that the model, simulator, judge, tool loop,
scoring, token accounting, and cost accounting work together before the full
100-task repeated measurement begins.

Validate the frozen execution plan without making a model call:

```bash
python scripts/run_model_smoke.py \
  --checkout /path/to/STATE-Bench \
  --output-dir /path/to/smoke-output \
  --agent-model-name <reported-model-name> \
  --agent-provider <azure_openai-or-openai>
```

Add `--execute` only after the preflight reports
`READY_FOR_TRAIN_SIDE_MODEL_SMOKE`. The runner fixes the smoke membership,
repeats, retrieval limit, and retry count. It writes an attempt ledger with
trajectory hashes, inline-scoring completeness, agent-side token and cost
accounting, process logs, and an explicit failure-cost boundary. Simulator and
judge provider costs require separate reconciliation.

Build a draft, size-matched candidate panel from a complete development
measurement:

```bash
python scripts/build_candidate_plan.py \
  --measurement starting-agent-measurement.json \
  --protocol PROTOCOL.json \
  --candidate-size 50 \
  --output candidate-plan.json
```

The draft contains four transparent choices:

- source-proportional hash sampling
- global deterministic random sampling
- static difficulty, which prioritizes tasks nearest 50% starting success while
  retaining source-proportional task-family quotas
- policy-relative selection, which prioritizes completion-signal density while
  retaining the same quotas.

The command fails when measurements are incomplete, a task family has no
mixed-outcome task, token accounting is missing, or two construction rules
produce the same membership. It never reads the held-out directory. A draft is
not a prospective freeze; the starting agent, learning operator, candidate
size, and complete run contract must still be fixed first.

## Freeze and score the prospective test

Copy [`RUN_CONTRACT.template.json`](RUN_CONTRACT.template.json), fill in the
starting agent and learning operator, and mark it `READY_TO_FREEZE`. The
contract must also state how retries and failed-attempt costs are recorded.
Then bind it to the candidate memberships and scoring rules:

```bash
python scripts/freeze_candidate_plan.py \
  --draft candidate-plan.json \
  --protocol PROTOCOL.json \
  --scoring-contract SCORING_CONTRACT.json \
  --run-contract run-contract.json \
  --output candidate-freeze.json
```

Before evaluation, retain each materialized learning artifact in its arm result
directory and create an `ARM_MANIFEST.json` beside it. The no-learning arm
omits the artifact:

```bash
python scripts/prepare_arm_manifest.py \
  --candidate-plan candidate-freeze.json \
  --arm policy_relative \
  --learning-artifact /path/to/policy-relative/policy-relative-learning.json \
  --learning-build-cost-usd <cost> \
  --learning-build-wall-time-seconds <seconds> \
  --output /path/to/policy-relative/ARM_MANIFEST.json
```

After all five arms finish the complete 50-task, five-run evaluation, open the
result files only to verify identities, hashes, and completeness. This gate
does not compute scientific aggregates:

```bash
python scripts/gate_candidate_results.py \
  --checkout /path/to/STATE-Bench \
  --candidate-plan candidate-freeze.json \
  --protocol PROTOCOL.json \
  --scoring-contract SCORING_CONTRACT.json \
  --arm no_learning=/path/to/no-learning \
  --arm source_proportional=/path/to/source-proportional \
  --arm deterministic_random=/path/to/random \
  --arm static_difficulty=/path/to/static-difficulty \
  --arm policy_relative=/path/to/policy-relative \
  --output release-gate.json
```

Score only after that gate passes, using the same five `--arm` arguments:

```bash
python scripts/score_candidate_results.py \
  --checkout /path/to/STATE-Bench \
  --candidate-plan candidate-freeze.json \
  --scoring-contract SCORING_CONTRACT.json \
  --release-gate release-gate.json \
  --arm no_learning=/path/to/no-learning \
  --arm source_proportional=/path/to/source-proportional \
  --arm deterministic_random=/path/to/random \
  --arm static_difficulty=/path/to/static-difficulty \
  --arm policy_relative=/path/to/policy-relative \
  --output results.json
```

The scorer reports held-out improvement, candidate ordering, allocation regret,
task and task-family regressions, user experience, cost, tool errors, redundant
calls, and disagreements between state and conversational requirements. Those
trace measurements are diagnostics. The contract does not label them as reward
hacking without a separate causal audit.

