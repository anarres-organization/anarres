# RFC 0004: Predictive decision records

- Status: proposed
- Date: 2026-11-10

## Context

Environment profiles record measurements made before training. They establish
that candidates were measured compatibly, but they do not establish that a
coordinate predicts downstream utility. Domain studies now produce three later
objects with recurring structure:

1. a forecast frozen before candidate outcomes are opened
2. task- or target-level regression-risk predictions made before training
3. a post-outcome score that evaluates the forecast and resulting decision

These objects currently remain in native study records. Legal reasoning exposes
a released regression evaluation, robotics preserves prospective decisions and
abstentions, and materials science has frozen a joint environment-selection and
target-regression protocol. A shared envelope could make these records easier
to inspect without flattening their domain-specific estimands.

## Proposed decision

Anarres should define three immutable record types after at least two native
adapters demonstrate the complete lifecycle:

- **Environment forecast:** predicted utility by candidate, target, and budget,
  together with uncertainty, support, measurement cost, and an optional
  selection or abstention.
- **Regression-risk forecast:** pre-training risk for named tasks or physical
  targets, including the regression endpoint, validation partition, calibrated
  probability, and prioritization threshold.
- **Decision score:** observed outcomes, curve error, ordering, allocation
  regret, interval coverage, regression discrimination and calibration, and the
  exact forecast artifact being scored.

Every record would identify:

- candidate profile digests and the starting subject
- target and compute-budget definitions
- predictor code, fit data, and fit-artifact digests
- development and prospective partitions
- evidence tier and temporal freeze status
- uncertainty method and abstention rule
- measurement, labeling, training, and evaluation costs
- domain-native artifacts and claim boundaries

The native CLI would validate identity, chronology, and record integrity. The
domain adapter would remain responsible for feature construction, fitting,
calibration, scientific units, and interpretation. A forecast record could not
be created from an environment profile alone.

## Staged adoption

The common schemas should not be merged with this proposal. Materials science
will first exercise the lifecycle through its study-local adapter:

1. expose the frozen pre-outcome protocol and baseline
2. train and score complete development environments
3. freeze forecasts and material-level regression risks for the prospective
   partition
4. open outcomes and produce a separate score

Legal and robotics records should then be projected into the same candidate
envelope without changing their native conclusions. Shared schemas become
eligible for acceptance only if those projections preserve their abstention,
uncertainty, cost, and regression semantics without study-specific exceptions.

## Consequences

This proposal gives the public API a path from measurement to prediction while
keeping scientific validation outside the Rust core. Users could inspect a
forecast, its support, and its later score through one operational envelope,
while the originating study remains authoritative.

The staged approach also prevents three errors: treating coordinate direction
as a validated decision rule, presenting retrospective fit as prospective
evidence, and reporting aggregate improvement without target-level regression
risk. Until the RFC is accepted, adapters may expose read-only study-local
reports with explicit schema names and evidence boundaries.
