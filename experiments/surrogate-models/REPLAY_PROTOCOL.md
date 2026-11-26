# Environment-selection replay protocol

**Evidence tier:** preregistered retrospective replay design. Running this
protocol on released outcomes does not create prospective evidence.

This protocol governs the second, cross-panel comparison. The bounded
[mathematics scale-transfer comparison](FIRST_COMPARISON.md) comes first and
validates the evaluator and information-boundary checks under one controlled
study.

## Question

Given a candidate panel, a starting policy, and a fixed candidate-training
budget, does adding compatible starting-policy measurements improve the choice
of environment after measurement and training costs are charged?

## Decision setting

Each replay episode contains:

- one candidate panel with a common starting policy, trainer, target, and
  candidate-training budget
- candidate metadata and measurements available before candidate training
- a history of earlier panels or revealed candidates permitted by the split
- native downstream outcomes for every candidate
- measurement, training, failure, and evaluation costs when recorded
- an action set containing every candidate and `retain_starting_policy`

The primary fixed-panel action is to choose one candidate or retain the
starting policy. Sequential acquisition is a secondary evaluation in which a
method may reveal a permitted probe or candidate outcome and then update.

## Prediction cutoff and leakage controls

For each candidate, construct the input from artifacts whose timestamps and
provenance precede that candidate's outcome. Exclude:

- trained-policy evaluations and later checkpoints
- post-outcome summaries, conclusions, and issue or pull-request text
- fields computed using candidate outcomes
- filenames, paths, labels, or hashes that deterministically identify a known
  outcome
- retrieved public records that violate the declared chronological cutoff

Text and code require a contamination audit because a pretrained language
model may already encode public outcomes. Report this exposure risk separately;
do not describe a public-record language-model evaluation as prospective.

## Splits

No random row split is allowed for the primary results. Use the strongest split
supported by each claim:

1. **Within-study interpolation:** hold out complete candidate environments and
   retain all of their seeds, checkpoints, and evaluation rows together.
2. **Scale transfer:** hold out one complete model scale.
3. **Study transfer:** hold out one complete experiment, including all
   candidates and derived records.
4. **Domain transfer:** hold out one complete domain. This is exploratory until
   more domains contain multiple comparable studies.
5. **Chronological transfer:** fit on records available before a date and score
   only later interventions.

Hyperparameters, feature selection, calibration, and abstention thresholds use
only the training portion of each split. Nested validation is required whenever
the same panels are used for model selection and final scoring.

## Baselines

Every method receives the same permitted history and action set.

1. retain the starting policy
2. random candidate selection
3. best candidate label or fixed native rule learned from prior panels
4. direct low-fidelity ranking from a short run or probe, when available
5. metadata-only ridge regression
6. metadata-plus-measurement ridge regression
7. a small tree ensemble with matched features
8. a calibrated Gaussian-process surrogate when sample size and feature space
   make it appropriate
9. a historical-performance representation with Bayesian ridge when candidate
   identities recur across panels
10. a frozen language model conditioned on the same retrieved records

A learned multimodal model is added only after these baselines run and the
number of independent interventions is sufficient for a prespecified training
and validation split.

This preserves the richer model family proposed in
[issue #94](https://github.com/anarres-organization/anarres/issues/94). It makes
model complexity conditional on evidence rather than removing it from the
program.

## Ablations

The central ablation holds the predictor and split fixed while changing its
inputs:

1. panel and candidate metadata only
2. metadata plus starting performance
3. metadata plus native starting-policy measurements
4. metadata plus measurements and permitted prior outcomes

Each added input reports its acquisition cost. Domain-native measurements stay
namespaced; absent coordinates remain missing rather than zero.

## Endpoints

### Primary

- mean allocation regret within panel
- best observed native utility as a function of total research cost
- probability of selecting a candidate that regresses relative to the starting
  policy

Regret is normalized only within a panel before aggregation. Native utility is
never pooled directly across domains.

### Secondary

- pairwise ordering accuracy within panel
- rank correlation when a panel has enough candidates
- native-unit prediction error
- interval coverage and width
- calibration of regression-event probabilities
- abstention rate and conditional regret after abstention
- cost to reach a prespecified utility threshold
- surrogate fit and inference cost

Report panel-macro and study-macro summaries. Candidate- or task-micro averages
are diagnostic because large panels would otherwise dominate the result.

## Sequential replay

For a sequential comparison, initialize every method with the same revealed
records. At each step the method selects one allowed measurement or candidate
training run. The replay reveals only that observation, charges its recorded
cost, and records the next decision. Candidate order, tie handling, update
frequency, and stopping rules are fixed before scoring.

Archive replay assumes that every candidate would have produced the same
outcome if selected adaptively. State this limitation. A real adaptive policy
requires a prospective execution because selection may change the candidate
distribution or later training state.

## Uncertainty and abstention

Training-seed variability, evaluation sampling error, and surrogate uncertainty
are distinct. A method may abstain when:

- the predicted margin is below a calibrated threshold
- interval overlap makes the decision unresolved
- the candidate lies outside measured support
- expected value after cost is below retaining the starting policy

Thresholds are fit inside the training fold. Report both coverage and regret so
abstention cannot appear successful merely by avoiding most decisions.

## Acceptance criteria for a prospective follow-up

The replay result warrants a frozen prospective test only if the selected
measurement-informed method:

1. improves study-macro allocation regret over the strongest simple baseline
   on complete-study holdouts
2. retains the improvement after measurement and surrogate costs are charged
3. does not increase regression selection relative to the strongest baseline
4. has an auditable prediction cutoff and reproducible record inventory
5. declares domains or candidate types on which it abstains

These criteria select a method for further testing. They do not establish a
general surrogate until the frozen prospective test is scored.

## Prospective follow-up

Before opening any new candidate outcome, freeze:

- starting policy, trainer, target, and budget
- candidate panel and membership hashes
- allowed measurements and their cost accounting
- predictor code, fit records, and fit-artifact digest
- acquisition rule, uncertainty method, and abstention threshold
- permitted sequential updates
- evaluation contract and independent units
- success, failure, and null-result reporting rules

The scored release should include every candidate outcome. A protocol that
explicitly studies partial execution may release the selected outcomes instead.

