# Prospective closed-loop curation on RoboMimic Can v1.4.1

**Status:** complete prospective comparison. Closed-loop qualification passed
with 95 successes and 5 failures across 100 episodes. Three-checkpoint
influence measurement passed its frozen reliability gate, five candidate sets
were serialized, and all 25 candidate policies were evaluated before the
outcome gate opened.

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

The exact frozen memberships are released in
[`CANDIDATES.json`](CANDIDATES.json). Candidate outcomes remain sealed until
all expected runs and evaluations pass the completeness and identity checks.
The machine-readable contract is in
[`PROTOCOL.json`](PROTOCOL.json), and source revisions and artifact hashes are
in [`SOURCES.json`](SOURCES.json).

The original `FREEZE.json` remains byte-for-byte unchanged.
`FREEZE_CORRECTION.json` records the source-manifest digest for the corrected
v1.4.1 dataset reference, and the validator checks both records.

## Prospective result

The frozen point prediction selected the tier-balanced CUPID subset. The
shortest-demonstration subset had the highest mean success rate, while the
frozen choice finished 1.4 percentage points behind it. The difference was
small relative to five-seed uncertainty: the paired bootstrap interval for the
frozen choice minus the length baseline was $[-3.4, 0.2]$ points.

| Candidate | Demonstrations | Mean success |
| --- | ---: | ---: |
| All data | 300 | 97.6% |
| Random 50% | 150 | 93.8% |
| Shortest 50% | 150 | **98.8%** |
| CUPID 50% | 150 | 97.6% |
| Tier-balanced CUPID 50% | 150 | 97.4% |

The frozen recommendation avoided the weak random subset and remained within
0.2 points of the all-data and unconstrained CUPID means. All four structured
choices outperformed random selection. The panel supports low-regret curation
within one high-performing Can setting, while the length baseline remains the
strongest rule in the panel.

[`RELEASE_GATE.json`](RELEASE_GATE.json) records the 25 checkpoint and outcome
hashes. [`OUTCOMES.json`](OUTCOMES.json) contains the compact released outcome
records, and [`RESULTS.json`](RESULTS.json) contains the scored prospective
comparison. Recompute it with:

```bash
python scripts/score_released_panel.py --output /tmp/can-v141-results.json
python -m unittest test_released_results.py
anarres robotics can-results --repository . --json
```

## Native CLI profiles

[`PROFILE_MEASUREMENTS.json`](PROFILE_MEASUREMENTS.json) is a compact public
record derived from the three native CUPID score files and the frozen candidate
memberships. It contains no candidate-policy outcomes or machine-specific
paths. The adapter exports one profile per candidate with CUPID rank position,
operator-tier coverage, demonstration length, and cross-checkpoint rank
reliability. Profile attributes retain the construction rule, tier-balance
correction, selected exposure, scoring-policy failure rate, and zero score
missingness without presenting them as additional fitted coordinates:

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
```

To qualify the native Can dataset before constructing a study workflow, place
the single `low_dim_v141.hdf5` artifact in its own environment directory and
record its pinned identity:

```bash
anarres init ./can-v141-source \
  --adapter robotics \
  --revision sha256:b6ceaed84c0335613a5001c900493b226481c132c792ec2cbdb99cb12c62baf0 \
  --license "DATASET-LICENSE"
anarres inspect ./can-v141-source
anarres qualify ./can-v141-source
```

Qualification verifies the exact dataset hash, HDF5 structure, and
demonstration inventory. It does not start training or open candidate outcomes.
The user records the applicable dataset terms because the upstream dataset is
distributed separately from the MIT-licensed RoboMimic code.

The released probe identity is recorded separately in
[`PROBE_CONTRACT.json`](PROBE_CONTRACT.json). It binds the source dataset, the
three-checkpoint scoring ensemble, the CUPID and CuraEval revisions, the
closed-loop rollout contract, the influence aggregation, and the distinction
between task failures and infrastructure failures. A dry preflight reports
which local artifacts conform without starting simulation:

```bash
anarres robotics probe-preflight --repository . \
  --dataset /data/low_dim_v141.hdf5 \
  --checkpoints /models/can-scoring-ensemble \
  --runtime /src/robotics-probe-runtime \
  --python /opt/robotics-probe/bin/python \
  --backend local --json
```

The adapter does not yet advertise the shared `policy-probe` capability. The
released record does not provide resolvable checkpoint artifacts, and a
portable end-to-end probe has not passed the release gate. The preflight keeps
those missing requirements visible rather than substituting a nearby runtime
or a newly trained checkpoint.

The study-specific planning and execution path is:

```bash
anarres robotics status --repository .
anarres robotics plan --repository . --output .anarres/can-v141.plan.json
anarres robotics prepare --repository . \
  --dataset /data/low_dim_v141.hdf5 \
  --output /work/can-v141-prepared.hdf5
anarres robotics bundle --repository . \
  --plan .anarres/can-v141.plan.json \
  --dataset /work/can-v141-prepared.hdf5 \
  --curaeval /src/CuraEval \
  --python /opt/curaeval/bin/python \
  --accelerator-name "NVIDIA B200" \
  --backend local --gpu-indices 0,1 \
  --output /work/can-v141-bundle
anarres robotics submit --bundle /work/can-v141-bundle --execute
anarres robotics gate --bundle /work/can-v141-bundle
anarres robotics score --bundle /work/can-v141-bundle
anarres robotics can-results --repository . --json
anarres robotics profile --repository . --output-dir .anarres/can-v141
anarres robotics verify --repository .
anarres robotics results --repository .
```

`anarres-robotics` retains the Python implementation and robotics-specific
records. The Rust CLI discovers it through the generic adapter protocol without
importing robotics dependencies. The workflow uses CuraEval revision
`bd94bbbd435c1ef55edfe244894e5468f3a5df2b`, verifies the official Can v1.4.1
dataset hash, and writes all four subset masks while leaving the all-data arm
unfiltered. The bound task matrix contains five arms and five seeds, or 25
equal-budget runs.

Training-time rollouts are disabled, matching the claim-bearing execution. Each
final checkpoint is evaluated separately under the frozen 100-episode contract.

The released `plan` command reconstructs the pre-outcome workload for
reproduction. `plan`, `prepare`, and `bundle` do not start training. A generated
launcher calls `run-task --execute` for each training task and then for the
matching 100-episode evaluation. The bundle records the Python package freeze
and refuses execution if it changes. `gate` requires every training and
evaluation completion record, rehashes the final checkpoints and logs, and
writes the sealed completeness record. Candidate outcomes can be scored only
after that gate passes. `score` then reports per-seed success rates, candidate
means, the observed winner set, and regret for the frozen point prediction.

The descriptor and Can `status`, `plan`, `profile`, `prepare`, `bundle`, and
`verify` commands do not open candidate-policy outcomes. The separate `results`
command recomputes the already released PushT score and states its narrow claim:
correct abstention in that panel is not selector superiority.

## Scope

This is one simulated manipulation task, one policy family, and one fixed
training budget. Success rates are near saturation, and the five-seed
comparison does not resolve a 1.4-point difference between the frozen choice
and the length baseline. Qualification, outcome gating, and native CLI
conformance protect the comparison boundary. Transfer requires a new task,
candidate bank, and outcome-blind prediction.
