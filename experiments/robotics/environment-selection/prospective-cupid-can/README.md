# Prospective closed-loop curation on RoboMimic Can

**Status:** measurement protocol frozen; candidate-policy outcomes have not
been generated.

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

## Candidate bank

Every 50% candidate contains 150 demonstrations. The bank contains:

- all 300 demonstrations, the incumbent
- a size-matched random subset
- the shortest 150 demonstrations, a competent practical baseline
- the 150 demonstrations with the highest merged CUPID rank
- the highest-ranked 50 demonstrations from each of the better, okay, and
  worse operator tiers.

The final arm is the Anarres recommendation when the influence measurement
passes its reliability gate. It combines target-sensitive influence with a
fixed coverage constraint instead of assuming that either signal is sufficient
alone. If the gate fails, the protocol abstains rather than replacing the rule
after seeing training outcomes.

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
  decision outputs;
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

