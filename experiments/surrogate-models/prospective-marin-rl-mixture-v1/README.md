# Prospective Marin RL-mixture study

**Status:** coordination draft. No candidate panel, forecast, training run, or
prospective result has been frozen.

This study asks whether measurements made under a starting policy can predict
which fixed-budget RL task mixture will improve a broad model while avoiding
capability regressions. Snowball is the proposed development model. A later
Mochi comparison is eligible only after the Snowball procedure is fixed and
scored.

The study is a prospective test of the
[domain-aware surrogate](../DOMAIN_AWARE_SURROGATE_PROTOCOL.md), not a new fit
to Marin's published outcomes. Real training and held-out evaluation remain
the verifier.

This proposal is based only on public Marin records and does not imply Marin's
endorsement or commitment of compute.

## Why Marin is a useful test

Marin has released the ingredients that earlier Anarres studies often lacked:
content-addressed task pools, explicit RL recipes, source-level holdouts,
checkpoint records, retained traces, cost accounting, and broad evaluation.
Its published Snowball and Mochi runs also show why environment selection is a
vector-valued decision. The same training campaign can improve one benchmark
and reduce performance on another.

The existing results are development context only. They do not form a valid
prospective comparison because the model, starting checkpoint, task mixture,
sampler, optimizer, learning rate, run length, checkpoint rule, and evaluation
policy differ across runs. The [public source audit](SOURCE_AUDIT.json) records
these boundaries and the current readiness blockers.

## Candidate environment

One candidate environment is one probability distribution over the same
pinned RL task populations under one fixed rollout, verifier, sampler, and
training contract. The initial source vocabulary follows Marin's Exp4
curriculum:

| Source family | Published Exp4 share |
| --- | ---: |
| Agentic software repair | 34.4% realized quota |
| Nemotron instruction following | 15.0% |
| TaskTrove | 12.0% |
| Reasoning Gym | 10.4% |
| OpenScience | 10.4% |
| Nemotron Ultra | 6.2% |
| Snowball Smartie | 5.8% |
| Eurus | 5.2% |

The shares are descriptive, not the candidate panel. The final study should
contain three or four mixtures chosen without reading their training outcomes.
Every candidate must use the same source revisions and task eligibility rules.
Only the mixture weights may differ.

[`CANDIDATE_PANEL_PROPOSAL.json`](CANDIDATE_PANEL_PROPOSAL.json) gives a
minimal three-candidate design for review. It holds the six-source nonagentic
block at 32 of 64 groups and exchanges only agentic software-repair groups for
instruction-following groups: 32/0, 22/10, and 12/20. The first two reproduce
publicly documented operational precedents; the third continues the same quota
exchange. This is a proposal, not a frozen panel.

The common 32-group block uses the published Exp4 proportions: eight
TaskTrove, seven Reasoning Gym, seven OpenScience, four Nemotron Ultra, three
Snowball Smartie, and three Eurus groups. Measuring each source once under the
starting policy allows every candidate profile to be computed by reweighting
the same probe bank. That reduces measurement cost and removes a source-sample
confound from the comparison.

## Staged execution

### 1. Qualify the common contract

Before measurement, freeze:

- one Snowball starting checkpoint
- exact task-pool revisions, licenses, exclusions, and content hashes
- one sampler, optimizer, learning rate, group size, batch size, rollout
  budget, verifier set, and checkpoint-selection rule
- the repaired evaluation policy and exact task identities
- infrastructure-failure and missing-grade handling
- the candidate-construction rule and total compute available to the study

The current Marin records identify unresolved prerequisites. These include the
portable Mochi preset gap, plain-decoding log-probability mismatch, partial
generation retention, known grader defects, and the absence of an isolated
optimizer and learning-rate result. The machine-readable protocol keeps the
study at `coordination_draft` while any required item remains unresolved.

### 2. Measure the candidates

Run repeated attempts from the frozen starting policy on every candidate. At a
minimum, preserve source, task, response tokens, valid reward, verifier status,
admission status, group identity, sample index, policy version, sampling
probability, loss-eligible tokens, generated-token cost, and infrastructure
validity. Compute source-level and candidate-level usable signal density,
effective prompt coverage, reward distributions, validity rates, cost, and
trace diagnostics. Do not treat an unavailable verifier result as reward zero.

Measurements and traces are inputs only if their transformation, availability
time, acquisition cost, and content digest are recorded before training.

### 3. Freeze forecasts

Before any candidate outcome is opened, write forecasts for:

- candidate ordering and expected downstream utility
- change on every predeclared capability target
- probability or warning level for each predeclared regression endpoint
- uncertainty, support, and abstention
- expected measurement, training, and evaluation cost
- the option to retain the starting policy

Compare the frozen domain route, learned history-support gate,
measurement-only predictor, a transparent mixture baseline, Marin's planned
default, and retaining the starting policy. The same prediction-time evidence
and cost accounting apply to every eligible method.

### 4. Execute the Snowball development panel

Train every candidate needed to score the declared comparison. Use matched
generated tokens and the same training and evaluation contract. Candidate
seeds, checkpoints, benchmark rows, and repeated evaluations remain nested
under their trained intervention.

Primary endpoints are pairwise ordering, normalized allocation regret,
capability-change calibration, regression discrimination and calibration,
selective regret, and utility after total research cost. Report each native
target separately before any aggregate.

### 5. Transfer to Mochi

Mochi becomes a prospective scale-transfer test only after the Snowball
development result fixes the measurement transform, surrogate route,
abstention rule, candidate-construction rule, and scoring contract. No Mochi
outcome may be used to select those choices.

## Current boundary

The checked-in [protocol](PROTOCOL.json) is deliberately incomplete. Candidate
identities, compute, seeds, target weights, model artifacts, and the final
evaluation revision require coordination with the experiment owners. Until
those fields are fixed, the validator must reject execution readiness.

Check the current state with:

```bash
python experiments/surrogate-models/prospective-marin-rl-mixture-v1/validate_protocol.py
```

