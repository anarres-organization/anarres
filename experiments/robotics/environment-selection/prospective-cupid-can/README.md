# Prospective closed-loop curation on RoboMimic Can

**Status:** the execution is invalidated because its dataset and simulator
variant did not match the intended CuraEval contract. No candidate policy was
trained.

This study asks whether target-sensitive measurements from a robot policy can
choose a useful training subset before any candidate policy is trained. It uses
the 300-demonstration RoboMimic Can multi-human dataset and the Diffusion Policy
implementation released with CuraEval.

The experiment separates two stages. First, three fixed all-data scoring
policies produce success-labelled closed-loop rollouts. CUPID performance
influence then estimates how each demonstration affects closed-loop return.
Second, those measurements deterministically construct a candidate bank. The
candidate memberships, point prediction, and abstention rule must be serialized
before candidate training begins.

## Execution audit

All three scoring checkpoints completed. Closed-loop panels were then collected
for seeds 2 and 3, and each contained 100 failures and no successes. The
reliability gate could not pass because CUPID's performance influence requires
both outcome classes.

A subsequent provenance audit found that the staged artifact was RoboMimic's
v1.5 Can dataset with a RoboSuite 1.5 environment contract. CuraEval's released
Can study instead specifies `low_dim_v141.hdf5` and RoboSuite 1.4.1. This
mismatch invalidates the execution as a test of the intended protocol. It may
explain the failed rollouts, but this record does not establish causality. The
influence computations were stopped, and candidate training did not begin.

The machine-readable evidence and artifact hashes are recorded in
[`RESULT.json`](RESULT.json). No candidate-policy outcome was generated or
opened. A new study must freeze the correct v1.4.1 artifact and qualify its
closed-loop policy before influence measurement.

## Candidate bank

Every 50% candidate contains 150 demonstrations. The bank contains:

- all 300 demonstrations, the incumbent
- a size-matched random subset
- the shortest 150 demonstrations, a competent practical baseline
- the 150 demonstrations with the highest merged CUPID rank
- the highest-ranked 50 demonstrations from each of the better, okay, and
  worse operator tiers.

The final arm was the Anarres recommendation if the influence measurement
passed its reliability gate. The execution was invalidated before candidate
training, so no arm was selected and the candidate bank remains an unevaluated
design.

## Frozen decision contract

The protocol fixes:

- three scoring checkpoints and 100 closed-loop rollouts per checkpoint
- the canonical CUPID influence aggregation and rank-merge rule
- deterministic candidate construction and tie-breaking
- five fresh training seeds per arm
- equal optimizer-step budgets and final-checkpoint evaluation
- 100 paired evaluation episodes per trained policy
- training seed as the primary statistical unit
- allocation regret, pair ordering, and seed-level uncertainty as the primary
  decision outputs
- complete accounting of measurement, training, and evaluation cost.

Candidate training outcomes remain sealed until every expected arm and seed is
complete and the identity audit passes. Published results for related CuraEval
conditions are not used to alter memberships, the decision rule, or the
evaluation contract.

The machine-readable contract is in [`PROTOCOL.json`](PROTOCOL.json). Run
`python scripts/validate_protocol.py` to validate its internal consistency and
verify the serialized [`FREEZE.json`](FREEZE.json) digest.

## Why this panel matters

The first prospective PushT panel validated uncertainty-aware abstention but
did not establish selector superiority. Retrospective cross-source analysis
also found that a fitted model did not improve on a practical rule. This panel
therefore tests a narrower and stronger claim: whether closed-loop,
policy-responsive influence plus explicit coverage can change a real training
decision beyond full-data, random, and length-based controls.

## Scope

This is one simulated manipulation task, one policy family, and one fixed
training budget. A positive result would support this measurement-and-decision
contract in that setting. It would not establish a general robot-data selector.

