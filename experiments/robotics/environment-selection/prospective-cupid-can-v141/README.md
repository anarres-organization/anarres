# Prospective closed-loop curation on RoboMimic Can v1.4.1

**Status:** protocol frozen. The all-data scoring policy must pass closed-loop
qualification before influence measurement or candidate training begins.

This study tests whether target-sensitive measurements from a robot policy can
choose a useful training subset before any candidate policy is trained. It uses
the official 300-demonstration RoboMimic Can multi-human
`low_dim_v141.hdf5` artifact and the Diffusion Policy implementation released
with CuraEval.

## Corrected execution contract

An earlier execution used RoboMimic's v1.5 dataset and simulator contract. Its
candidate stage never started, and its record is preserved separately as an
invalidated execution variant. This study begins from a new freeze with the
v1.4.1 dataset hash and embedded RoboSuite 1.4.1 metadata verified before any
training.

The first all-data scoring checkpoint receives 100 closed-loop evaluation
episodes. The study proceeds only if those episodes contain both successes and
failures, the outcome support required by CUPID performance influence. Passing
qualification triggers the remaining scoring checkpoints, influence
measurement, and deterministic candidate construction. Failing qualification
returns a frozen abstention before those costs are incurred.

## Candidate decision

The candidate bank compares all 300 demonstrations with four 150-demonstration
alternatives: a fixed random subset, the shortest demonstrations, the highest
merged CUPID ranks, and a tier-balanced CUPID selection. Five fresh training
seeds are used per arm under equal optimizer-step budgets. Candidate identities,
the point prediction, training rules, and paired evaluation contract are fixed
before candidate training.

Candidate outcomes remain sealed until all expected runs and evaluations pass
the completeness and identity checks. The machine-readable contract is in
[`PROTOCOL.json`](PROTOCOL.json), and source revisions and artifact hashes are
in [`SOURCES.json`](SOURCES.json).

## Scope

This is one simulated manipulation task, one policy family, and one fixed
training budget. The qualification gate protects the influence measurement. It
does not establish selector performance, which requires the complete candidate
comparison.
