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

Marin also has a closer intermediate check. Its public
[mixture-swap ladder](https://github.com/marin-community/marin/issues/9126)
compares two pretraining environments at d768, d1024, and d1536, with a
three-seed d512 development comparison from one common checkpoint. This is
useful for backtesting cross-scale environment representation on the same model
family. It remains separate from the RL claim: pretraining mixture transfer
does not establish Snowball-to-Mochi post-training transfer.

The pinned d512 mixture-search swarm is a substantially larger development
set. It contains 934 trained continuations representing 915 distinct two-phase
mixtures. Every run belongs to the same from-10%-checkpoint swarm and training
recipe and reports the same 54 capability metrics plus 108 held-out loss and
bits-per-byte metrics. The public comparison explicitly verifies the exact
shared step-393 checkpoint for its three selected-mixture and three baseline
runs; the broader swarm metadata does not restate that checkpoint for every
row. The
[Grug swarm corpus](GRUG_SWARM_CORPUS.json) preserves the full 200-cell mixture
for each of two phases and stores outcomes separately from model inputs.
Repeated runs of the same mixture share one lineage identifier and must remain
in the same fold.

This is the first Marin archive large enough to train an environment surrogate
rather than only replay its record format. It is still development evidence:
the swarm helped select the published mixture, contains one model and one
budget, and tests pretraining mixtures rather than RL environments. Evaluation
must hold out complete mixture lineages and complete design families. The
larger mixture-swap ladder then tests whether the learned d512 ordering transfers
to d768, d1024, and d1536 before any Snowball-to-Mochi claim is considered.

The checked-in corpus can be inspected without optional dependencies. To
rebuild it, download the four files named in
[`GRUG_SWARM_SOURCE.json`](GRUG_SWARM_SOURCE.json) from the pinned Hugging Face
revision and run:

```bash
python experiments/surrogate-models/prospective-marin-rl-mixture-v1/build_grug_swarm_corpus.py \
  --source-dir /path/to/h100-d512-from10pct-store-4d2e363d
python -m unittest \
  experiments/surrogate-models/prospective-marin-rl-mixture-v1/test_grug_swarm_corpus.py
```

## First mixture-surrogate result

Marin had already developed and preregistered a content-aware Hellinger
surrogate in [issue 7067](https://github.com/marin-community/marin/issues/7067)
and its linked implementation. The analysis here reproduces that model family
for Anarres and extends the readout to all 162 native targets, repeated-run
lineage grouping, complete design-family holdouts, allocation regret,
support-based abstention, and target-level relative harm. The modeling method
originates in Marin; the grouped decision and harm audit is the Anarres
extension.

The [transparent baseline audit](GRUG_SWARM_BASELINE_RESULTS.json) compares a
training-fold mean, linear ridge, and two Hellinger-RBF kernels. The first
kernel uses the 400 raw mixture weights. The second maps each phase through
Marin's released 200-by-1,000 lexical content basis before fitting. Identical
mixtures stay in the same fold, and repeated runs are averaged by mixture
before ordering or allocation is scored.

When the held-out mixtures come from represented construction families, the
content kernel reaches 78.9% pairwise ordering and 0.059 normalized allocation
regret. When one complete construction family is absent from training, it
reaches 66.7% family-macro ordering and 0.154 regret, compared with 50.0% and
0.297 for the training-fold mean. The raw kernel reaches 76.4% and 63.1%
ordering on the same splits. The content representation therefore helps under
both tests without introducing protected outcomes, but extrapolation to a new
construction process remains substantially harder.

The support gate uses only the candidate content representation's distance
from the training mixtures. It accepts 95.0% of ordinary lineage holdouts;
accepted predictions have 0.22 mean standardized absolute error, compared
with 1.85 for rejected predictions. When a complete construction family is
held out, acceptance falls to 64.6%. Accepted error is 0.32 and rejected error
is 1.54. The gate therefore detects higher-error extrapolations and gives the
surrogate a concrete abstention path.

The published selected mixture and Harrier baseline provide a separate
development diagnostic. With both lineages excluded from fitting, the kernel
predicts the direction of 70.4% of the 54 capability metrics and 98.1% of the
108 held-out loss or bits-per-byte metrics. These metrics are related outcomes,
not 162 independent experiments. The swarm was also used to select the
published mixture, so this is not independent validation.

The [relative-harm audit](GRUG_SWARM_RELATIVE_HARM_RESULTS.json) extends this
comparison to all 914 non-reference mixture lineages and 162 native targets.
The released Harrier mixture is excluded from fitting and used as an
already-run reference. Under complete design-family holdout, the content
kernel reaches 0.803 target-macro ROC AUC and 0.801 average precision for
identifying target metrics that are worse than the reference. The highest-risk
20% contains 29.5% of observed regressions, a 1.48-fold recall lift. This is a
retrospective triage result, not calibrated risk: targets are correlated, only
three reference runs are available, and the zero-margin regression label does
not distinguish small changes from material harm. A prospective panel must
freeze that margin before candidate outcomes are opened.

The Grug kernel audits require every non-floating-point field to reproduce
exactly. Floating-point summaries use an absolute tolerance of 0.001 because
dense linear algebra can differ slightly across BLAS implementations. This is
below the precision used for the reported scientific conclusions and prevents
platform-specific numerical noise from masquerading as a stale artifact.

The [scale-transfer stress test](GRUG_SCALE_TRANSFER_RESULTS.json) compares the
d512 predictions with the released d768, d1024, and d1536 mixture-swap ladder.
Direction accuracy is 56.2%, 62.5%, and 81.2%, respectively, matching the
transfer of the observed d512 directions on this 16-subset comparison. The
larger runs start the selected schedule after 25% of training, while the d512
swarm starts from a checkpoint after 10%. These are useful transfer
diagnostics, but not an identical-contract scale test.

## First executable replay

The [Snowball closure replay](SNOWBALL_CLOSURE_REPLAY.json) converts one public
campaign into the record structure required by the surrogate proposal. It
contains three separately trained two-update recipes from one initializer.
Each recipe has four matched capability outcomes, while the six serving
repetitions per capability remain nested observations rather than additional
training records.

The builder writes prediction-time inputs and protected outcomes to separate,
content-addressed JSON Lines files. Starting-policy measurements and candidate
configuration are available to a predictor; candidate results are not. The
replay also keeps regressions target-specific: it does not average BFCL,
HumanEval+, IFBench, and MATH500 into a new utility score.

This replay tests the multi-target record contract. It does not establish
cross-study transfer, and it is not added to the existing scalar utility corpus.
Mochi outcomes remain absent.

Rebuild and check it with:

```bash
python experiments/surrogate-models/prospective-marin-rl-mixture-v1/build_snowball_closure_replay.py
python experiments/surrogate-models/prospective-marin-rl-mixture-v1/build_snowball_closure_replay.py --check
python -m unittest experiments/surrogate-models/prospective-marin-rl-mixture-v1/test_snowball_closure_replay.py
```

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
four-candidate design for review. It fixes nine Exp5 source shares at a
combined 65% and exchanges only agentic software-repair experience for
instruction-following experience within the remaining 35%. One candidate is
the released Exp5 allocation; the other three lie on the same mixture axis.
This is a proposal, not a frozen panel.

[`PROBE_BANK_PROPOSAL.json`](PROBE_BANK_PROPOSAL.json) specifies the smallest
shared starting-policy bank that can measure those candidates without changing
sample size. Each candidate contains 200 prompt groups and eight attempts per
group. Largest-remainder allocation fixes source quotas, while a seeded hash
orders prompt groups within each source. Fixed-source memberships are identical
across candidates, and the two exchanged sources use nested prefixes. The
shared bank therefore needs 245 unique prompt groups and 1,960 attempts rather
than four separately sampled candidate banks.

After the starting-policy bank is complete, a new immutable contract must bind
the panel, bank, selection seed, source mapping, and derivation implementation.
[`derive_snowball_candidate_measurements.py`](derive_snowball_candidate_measurements.py)
then computes equal-size candidate profiles. It refuses an unfrozen contract,
changed input, missing source support, malformed group, or duplicate identity.
The derivation creates prediction-time measurements only and cannot authorize
candidate training or open outcomes.

[`freeze_snowball_measurement_contract.py`](freeze_snowball_measurement_contract.py)
implements the earlier measurement freeze. It requires a portable starting
checkpoint and content digest, tokenizer digest, passed rollout-runtime checks,
and a qualified manifest for all eleven sources. Every source must pin its
revision, license, task-pool digest, verifier revision, and enough eligible
prompt groups for its largest candidate prefix. The resulting contract embeds
the exact metadata consumed by the probe-bank aggregator and binds all input
artifacts by digest. The currently released files intentionally fail this gate:
the cited starting-policy record has no portable checkpoint revision, and no
complete source or runtime qualification has been frozen for this study.

## Staged execution

### 1. Reconstruct the public development archive

Extract immutable model, data, recipe, evaluation, outcome, and cost records
from the public Snowball and Mochi campaigns. Preserve one row per trained
intervention. Checkpoint evaluations and repeated serving runs remain nested
under that intervention and never become additional training examples.

Use the d512 Grug swarm as a separate pretraining development corpus. Fit the
complexity ladder on mixture inputs only, keep all runs from one mixture in the
same fold, and hold out complete design families. Score all 162 released
metrics within their two declared families before any aggregate. Report
family-macro ordering and allocation regret alongside
pair-weighted results. Use the d768/d1024/d1536 mixture-swap results only as the
cross-scale stress test; do not use them to select the d512 model.

Use completed Snowball campaigns to test whether pre-training measurements
would have ordered observed interventions or warned about their localized
regressions. Use the Delphi ladder only as a separate method check. Do not use
Mochi outcomes to select the final transfer rule.

The [Micro210 pair audit](SNOWBALL_MICRO210_PAIR_AUDIT.json) identifies five
Snowball SFT-to-RL interventions from Exp2 through Exp6 evaluated under the
same frozen policy. Four improve aggregate pass@1 and one declines; the mean
change is 3.98 percentage points. These are currently outcome pairs rather
than surrogate-training records. Each experiment changes several recipe
properties, only aggregate public values have been reconstructed here, and
five interventions cannot support model fitting. Exact environment records,
starting-policy measurements, native benchmark rows, and runtime differences
must be joined before these pairs can enter the development corpus.

Exp5 is the first pair with enough public detail to close most of that join.
The [normalized intervention record](SNOWBALL_EXP5_INTERVENTION.json) preserves
its exact eleven-source sampling policy, route quotas, input hashes, training
contract, evaluation policy, and all 17 comparable native targets. It
reproduces an average 4.24-point improvement alongside four target
regressions. This is an outcome reconstruction, not a retrospective
prediction: no released starting-policy probe measures the experience that
the Exp5 environment provided before RL, and no matched alternative was
trained under the same contract. The record is therefore excluded from
surrogate fitting while defining the exact input and output fields the
prospective study must produce.

The public SFT seal pins the Exp5 starting-policy recipe revision, completed
update, certified model-manifest digest, and evidence-seal digest. It does not
publish a portable checkpoint revision in the cited record. The initializer's
identity is therefore reconstructable, but a future execution contract must
still bind and qualify the exact checkpoint artifact it will load.

The [candidate-panel proposal](CANDIDATE_PANEL_PROPOSAL.json) now uses that
released Exp5 contract as its anchor. It fixes nine source shares and exchanges
only software-repair and instruction-following experience across four
allocations, including the exact Exp5 allocation. This makes the prospective
decision identifiable: candidate ordering, target-level change, regression
warnings, and allocation regret can all be scored under one trainer and
evaluation policy. The panel remains a coordination proposal. It does not
authorize training until its sources, runtime, budget, seeds, probes, and
target weights are frozen.

The prospective [release scorer](score_snowball_panel.py) is implemented before
candidate outcomes exist. Once a scoring contract binds the final prediction
receipt and this script, it will reject incomplete candidate or seed matrices
and report target-change RMSE, interval coverage, pairwise ordering, allocation
regret against the option not to train, and regression ROC AUC, average
precision, Brier score, and recall in the highest-risk 20 percent. Its
uncertainty interval resamples whole training seeds jointly across candidates.
Targets and seeds remain nested observations rather than additional training
interventions. Every seed must match the frozen generated-token budget within
its declared tolerance. Measurement, training, and evaluation accelerator
hours are reported separately; the scorer does not invent a utility-to-cost
exchange rate.

The [probe-bank aggregator](aggregate_snowball_probe_bank.py) provides the
prediction-time input path. It validates the exact policy and source
revisions, requires every scheduled sample identity, separates infrastructure
and verifier failures from scientific rewards, computes admitted
leave-one-out advantage mass, and reports source-level signal density,
effective prompt coverage, reward distributions, validity, trace failure, and
token cost. The four candidates must be derived from this same source-stratified
bank using a rule frozen after the bank is collected and before any candidate
training. The aggregator deliberately stops at source evidence; it cannot
quietly choose candidate weights or prompt memberships.

The current probe-bank and candidate-panel files are coordination proposals.
They fix enough structure for review and cost estimation, but they do not
authorize probe collection. Starting-policy and runtime identities, source
revisions, licenses, qualification rules, and the complete attempt budget must
be accepted in a separate immutable freeze first.

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

