# Prospective Marin RL-mixture study

**Status:** public-evidence reconstruction and prospective-design draft. No
candidate panel, forecast, new training run, or prospective result has been
frozen.

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

The existing results are development evidence, not a prospective comparison.
The model, starting checkpoint, task mixture, sampler, optimizer, learning
rate, run length, checkpoint rule, and evaluation policy differ across runs.
The [historical RL inventory](HISTORICAL_RL_INVENTORY.json) records which
comparisons can train a surrogate, which are descriptive only, and which are
invalid for ordering candidates. The [public source audit](SOURCE_AUDIT.json)
records the remaining readiness blockers.

## What can be reconstructed publicly

The study does not require experiment owners to restate information that Marin
has already published. Public issues, pinned recipes, model releases, campaign
archives, and evaluation seals already identify much of the Snowball and Mochi
history. The reconstruction stage extracts those records first and reports any
field that cannot be verified from a public artifact.

The [model-ladder audit](MODEL_LADDER_AUDIT.json) distinguishes three kinds of
evidence:

1. Marin's five-rung Grug pretraining ladder, from 61 million to 22.8 billion
   active parameters, establishes a genuine same-recipe pretraining scale
   sequence.
2. Snowball is a 67B-total, approximately 2B-active Grug model used by Marin as
   the smaller post-training proxy for Mochi. Mochi is the post-trained 535B
   Hero model. Snowball and Mochi therefore support a cross-scale transfer
   test.
3. The public record does not contain matched RL environment interventions at
   every pretraining rung. Snowball and Mochi alone do not establish an RL
   scaling law. The smaller rungs must first be checked for artifact access and
   post-training runtime compatibility, then run under one matched contract if
   they are to become scaling-law observations.

Marin's completed Delphi RL scaling study is useful for testing the analysis
and uncertainty machinery, but it is a different model family and cannot stand
in for Grug-family transfer.

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

### 1. Reconstruct the public development archive

Extract immutable model, data, recipe, evaluation, outcome, and cost records
from the public Snowball and Mochi campaigns. Preserve one row per trained
intervention. Checkpoint evaluations and repeated serving runs remain nested
under that intervention and never become additional training examples.

Use completed Snowball campaigns to test whether pre-training measurements
would have ordered observed interventions or warned about their localized
regressions. Use the Delphi ladder only as a separate method check. Do not use
Mochi outcomes to select the final transfer rule.

### 2. Qualify the Grug ladder and common contract

Check every published narrow Grug rung for a durable final checkpoint,
tokenizer and template compatibility, serving support, and the ability to load
the common SFT and RL runtime. This is a qualification step, not a claim that
pretraining loss predicts RL utility.

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
generation runtime certification, known grader defects, and the absence of an
isolated optimizer and learning-rate result. The machine-readable protocol
keeps new execution unauthorized while any required item remains unresolved.

### 3. Measure the candidates

Run repeated attempts from the frozen starting policy on every candidate. At a
minimum, preserve source, task, response tokens, valid reward, verifier status,
admission status, group identity, sample index, policy version, sampling
probability, loss-eligible tokens, generated-token cost, and infrastructure
validity. Compute source-level and candidate-level usable signal density,
effective prompt coverage, reward distributions, validity rates, cost, and
trace diagnostics. Do not treat an unavailable verifier result as reward zero.

Measurements and traces are inputs only if their transformation, availability
time, acquisition cost, and content digest are recorded before training.

### 4. Freeze forecasts

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

### 5. Execute the scale ladder and Snowball development panel

If the narrow Grug checkpoints pass qualification, select the smallest set of
rungs that spans the available active-parameter range and run the same fixed
candidate contract on each. Qualifying every rung does not require training
every rung: the selection rule must be written before outcomes and must retain
enough distinct scales to test a trend. Report cross-scale transfer until at
least three scales have matched interventions; reserve the term *RL scaling
law* for that stronger design.

Train every candidate needed to score the declared comparison. Use matched
generated tokens and the same training and evaluation contract. Candidate
seeds, checkpoints, benchmark rows, and repeated evaluations remain nested
under their trained intervention.

Primary endpoints are pairwise ordering, normalized allocation regret,
capability-change calibration, regression discrimination and calibration,
selective regret, and utility after total research cost. Report each native
target separately before any aggregate.

### 6. Transfer to Mochi

Mochi becomes a prospective scale-transfer test only after the Snowball
development result fixes the measurement transform, surrogate route,
abstention rule, candidate-construction rule, and scoring contract. No Mochi
outcome may be used to select those choices.

## Current boundary

The checked-in [protocol](PROTOCOL.json) is deliberately incomplete because it
describes a future prospective experiment. Public reconstruction can fill
historical model, data, recipe, evaluation, outcome, and cost fields. It cannot
infer choices that have not yet been made: the final candidates, replicate
seeds, compute budget, target weights, and prediction receipt. Runtime and
grader repairs also need evidence that they pass their published gates. Until
those future choices and gates are fixed, the validator must reject execution
readiness.

Check the current state with:

```bash
python experiments/surrogate-models/prospective-marin-rl-mixture-v1/validate_protocol.py
```

