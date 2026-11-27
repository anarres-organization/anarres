# Domain-centered surrogate protocol

**Status:** frozen retrospective development corpus. No general or prospective
surrogate claim is made.

## Question

Can one prediction system use evidence available before training to answer four
questions for a candidate environment?

1. How much will the declared target improve?
2. Which tasks, materials, or behavior groups are likely to regress?
3. What will measurement, training, and evaluation cost?
4. Is the evidence strong enough to select a candidate, acquire another
   measurement, or retain the starting policy?

The system must preserve each study's native target and units. It does not fit a
single utility scale across domains.

## Evidence in this release

[`DOMAIN_SURROGATE_INVENTORY.json`](DOMAIN_SURROGATE_INVENTORY.json) and
[`DOMAIN_SURROGATE_RECORDS.jsonl`](DOMAIN_SURROGATE_RECORDS.jsonl) contain the
development view for legal, robotics, materials science, finance, and agentic
coding. Mathematics remains in the first replay as a conformance fixture rather
than headline supervision.

The inventory separates two related prediction tracks:

- **Intervention utility:** one row is an independently trained intervention or
  an explicitly marked publication-derived candidate aggregate. Outcomes are
  compared only within their native candidate panel.
- **Localized regression risk:** one row can describe a task, target material,
  or evaluation stratum, but remains nested under its training intervention.
  These rows do not increase the number of independent interventions.

Finance currently contributes utility comparisons but no released localized
regression labels. That missing evidence remains explicit.

## Current regression evidence

The inventory recomputes or records the released held-out metrics and their
boundaries:

- Legal and agentic coding provide retrospective task-risk analyses within one
  training study each.
- Robotics provides a prospective ordering of evaluation-stratum risk, not a
  calibrated regression-event model.
- Materials science froze target-level probabilities before opening four
  candidate outcomes. On those 200 candidate-material pairs, the resulting ROC
  AUC is 0.494. This is a prospective miss and must remain part of the model
  selection record.

These results show that regression prediction is not solved by joining the
records. Each domain needs compatible target features, grouped validation, and
an explicit transfer claim.

## Development suites

[`DOMAIN_SURROGATE_SPLITS.json`](DOMAIN_SURROGATE_SPLITS.json) freezes five
grouped suites:

- controlled legal, robotics, and materials studies, holding out one complete
  study
- agentic coding, holding out one complete training decision and all of its
  endpoints
- materials science, holding out one complete study
- finance, holding out one complete study
- a deliberately exploratory complete-domain holdout

Every model choice, retrieval rule, prompt, feature transform, and calibration
method must be selected inside the training portion of a fold. Tasks,
endpoints, targets, checkpoints, evaluation samples, and repeated seeds remain
with their parent study or decision.

## First structured replay

[`DOMAIN_STRUCTURED_RESULTS.json`](DOMAIN_STRUCTURED_RESULTS.json) records the
first grouped development replay. Starting-policy and domain measurements
produce 81.5% pairwise ordering in coding, 71.0% in finance, and 62.3% in
materials science. The best normalized regrets are 0.053, 0.235, and 0.323,
respectively. The controlled five-study suite remains at 50% ordering and 0.527
regret for every eligible fitted method.

This pattern rules out a pooled headline result. It instead establishes three
development tracks with measurable signal and one sparse transfer test where
the present representation has no demonstrated value. A stronger model must
improve the held-out decisions in that sparse suite without giving up the
domain-specific results. Model scale alone is not an accepted explanation.

## Model comparison

The comparison uses the same information cutoff and candidate panels for every
method:

1. uninformed and released domain-native rules
2. metadata-only linear and tree models
3. structured domain measurements
4. Gaussian-process or ensemble predictors where the fold has enough support
5. semantic nearest-neighbor retrieval
6. a record-conditioned language model without retrieved outcomes
7. the same model with development-selected retrieved records
8. domain-native trajectories, structures, curves, text, or code only through
   explicit held-out ablations

Changing the language-model backbone after observing a held-out result is not a
valid improvement. Backbone, retrieval, and reasoning settings are development
choices. A more capable model advances only if it improves grouped decision
metrics over the strongest simpler method.

## Required outputs

For each candidate, the surrogate returns:

- a native-unit target forecast and interval when the target is comparable
- within-panel ordering and expected allocation regret
- localized regression probabilities for supported targets
- measurement, training, and evaluation cost fields, with missing cost retained
- support evidence and an explicit select, measure, or abstain action

Verbal confidence is not an uncertainty estimate. Intervals and event
probabilities require held-out calibration.

## Advancement gate

The already scored six-study replay is closed for model selection. The next
candidate method is chosen on the new development suites, then serialized
before a new complete study or prospective candidate panel opens outcomes.

A method advances only if it:

1. improves study-macro allocation regret or pairwise ordering over the
   strongest simple baseline after measurement and inference cost.
2. reports regression calibration separately from utility ranking.
3. detects unsupported inputs and abstains under a frozen rule.
4. preserves real training and protected evaluation in the loop.

The surrogate may choose what to execute. It does not verify its own forecast.
