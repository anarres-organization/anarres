# Prospective closed-loop curation on RoboMimic Can v1.4.1

**Status:** closed-loop qualification passed with 95 successes and 5 failures
across 100 episodes. Three-checkpoint influence measurement passed its frozen
reliability gate, and five candidate sets were serialized before their policy
outcomes opened.

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

The corrected policy passed this gate with both outcome classes present. The
machine-readable counts and artifact hashes are recorded in
[`QUALIFICATION.json`](QUALIFICATION.json). This result qualifies the
measurement pipeline. It does not reveal candidate-policy performance.

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

## Native CLI profiles

[`PROFILE_MEASUREMENTS.json`](PROFILE_MEASUREMENTS.json) is a compact public
record derived from the three native CUPID score files and the frozen candidate
memberships. It contains no candidate-policy outcomes or machine-specific
paths. The adapter exports one profile per candidate with CUPID rank position,
operator-tier coverage, demonstration length, and cross-checkpoint rank
reliability:

```bash
uv run python \
  experiments/robotics/environment-selection/prospective-cupid-can-v141/export_environment_profiles.py \
  --output-dir .anarres/can-v141

cargo run --quiet -p anarres-cli -- qualify \
  .anarres/can-v141/can-v141-cupid_50.profile-input.json

for profile in .anarres/can-v141/*.profile-input.json; do
  cargo run --quiet -p anarres-cli -- measure "$profile" \
    --output "${profile%.profile-input.json}.profile.json"
done

cargo run --quiet -p anarres-cli -- design \
  .anarres/can-v141/*.profile.json
```

The adapter verifies the protocol, source, qualification, checkpoint, score,
and membership identities before export. CLI compatibility means that the five
candidates share one scientific contract. It does not reveal which candidate
performs best after training.

The study-local command can be installed independently from the native CLI:

```bash
uv tool install \
  ./experiments/robotics/environment-selection/prospective-cupid-can-v141
anarres adapter doctor robotics
anarres robotics status --repository .
anarres robotics profile --repository . --output-dir .anarres/can-v141
anarres robotics verify --repository .
```

`anarres-robotics` retains the Python implementation and robotics-specific
records. The Rust CLI discovers it through the generic adapter protocol without
importing robotics dependencies. The descriptor and `status` command do not
open candidate-policy outcomes.

## Scope

This is one simulated manipulation task, one policy family, and one fixed
training budget. Qualification and native CLI conformance protect the
measurement and comparison boundary. Selector performance requires the
complete, separately gated candidate comparison.
