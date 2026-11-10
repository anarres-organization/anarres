# Prospective SylloGym mixture selection

**Status:** complete prospective decision record with an explicit chronology
caveat.

The study compares three allocations over the same fourteen SylloGym task
generators:

- **Published depth-weighted control:** a competent task-depth allocation based
  on the public study.
- **Uniform control:** equal allocation across the fourteen generators.
- **Policy-response allocation:** a frozen mixture based on starting-policy
  readiness, eligible-response availability, reward discrimination, token cost,
  truncation, reliability, and missingness, with a coverage floor.

The allocation rule and realized exposure manifests were frozen before
candidate training. The four-percentage-point smallest effect of interest and
final interpretation rule were fixed after training started but before target
evaluation or outcome opening. The release preserves that distinction rather
than describing the entire analysis as preregistered before launch.

## Matched contract

| Component | Frozen value |
| --- | --- |
| Environment | SylloGym at `87b0427fa0b98bef8ee62568169bcc218d3eef7c` |
| Starting policy | `unsloth/Qwen3-4B-unsloth-bnb-4bit` at `bbe12ebf9362b3bcbf44e826e4c98910f2c02e72` |
| Candidate arms | Published weighting, uniform weighting, policy-response weighting |
| Training | 180 optimizer updates, eight generations per prompt |
| Training seeds | 42, 43, 44 |
| Evaluation | The same 45 task generators and 900 episodes per arm-seed |
| Primary endpoint | Equal-task macro all-turn episode completion |
| Smallest effect of interest | 4 percentage points |
| Material family-regression threshold | -5 percentage points |
| Independent unit | Paired training seed |

Only the realized exposure counts over the fourteen training generators differ
between arms. The execution uses a three-by-three balance: every arm appears
once on each of three execution devices, and every training seed spans all
three devices.

## Results

| Mixture | Seed 42 | Seed 43 | Seed 44 | Mean | Regret |
| --- | ---: | ---: | ---: | ---: | ---: |
| Published depth-weighted | 76.44% | 77.89% | 77.11% | 77.15% | 0.37 pp |
| Uniform | 76.22% | 76.67% | 78.33% | 77.07% | 0.44 pp |
| Policy-response | 78.44% | 77.00% | 77.11% | **77.52%** | **0.00 pp** |

The policy-response allocation was the observed best arm. Its mean advantage
was 0.37 points over the published control and 0.44 points over uniform. The
corresponding training-seed 95% intervals were -3.31 to 4.05 and -3.84 to 4.73
points. Neither contrast approached the four-point decision threshold with
adequate precision. No task-family point estimate crossed the frozen -5-point
regression threshold.

The correct decision is therefore:

> Abstain. The frozen rule ranked the observed best mixture, but the estimated
> advantage is too small and uncertain to justify replacing the controls.

## Historical-result boundary

The public SylloGym article and model card identify a Qwen3-4B intervention,
while a checked-in evaluation notebook identifies a different model size and
does not fully pin the outcome-producing runtime. This release does not use that
historical result as causal supervision and does not claim to reproduce it.

The prospective panel avoids that ambiguity by starting every arm from the same
newly pinned weight bytes and running every arm under one matched contract.

## Reproduce the score

```bash
cd experiments/legal/environment-selection
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The script recomputes means, allocation regret, paired seed contrasts, t
intervals, the family-regression gate, and the abstention decision from the
compact public record.

## Export pre-training environment profiles

The release includes the outcome-blind component measurements used before
candidate training. The adapter verifies their hashes, source and policy pins,
attempt identities, reliability gates, frozen weights, and prospective
chronology before projecting the three mixtures into the shared Anarres profile
contract.

```bash
uv tool install ./packages/legal
anarres adapter doctor legal
anarres legal profile --repository . --output-dir /tmp/syllogym-profiles

cargo run --quiet -p anarres-cli -- qualify \
  /tmp/syllogym-profiles/frozen_policy_response_allocation.profile-input.json
cargo run --quiet -p anarres-cli -- measure \
  /tmp/syllogym-profiles/frozen_policy_response_allocation.profile-input.json \
  --output /tmp/syllogym-policy-response.profile.json
```

The profiles contain no downstream outcomes. They preserve the measured
candidate properties and provenance needed for comparison, while the released
decision record remains authoritative for prospective interpretation.
`anarres legal status` reports the SylloGym and LAB evidence as separate
scientific objects. LAB regression-risk results are never profile inputs.

## Files

- [`data/frozen-decision.json`](data/frozen-decision.json): pre-outcome rule,
  chronology, source pins, and mixture weights.
- [`data/pretraining-task-measurements.json`](data/pretraining-task-measurements.json):
  outcome-blind component measurements for fourteen task generators.
- [`data/selector-freeze.json`](data/selector-freeze.json): frozen candidate
  weights and qualification gates.
- [`data/measurement-release.json`](data/measurement-release.json): source,
  policy, contract, and native-artifact digest bindings.
- [`data/outcomes.json`](data/outcomes.json): nine arm-by-seed outcomes,
  guardrail contrasts, and aggregate compute receipts.
- [`results/summary.json`](results/summary.json): deterministic derived result.
- [`scripts/reproduce.py`](scripts/reproduce.py): standard-library analysis.
- [`scripts/export_environment_profiles.py`](scripts/export_environment_profiles.py):
  fail-closed native profile adapter.
- [`test_reproduce.py`](test_reproduce.py): scientific integrity checks.
- [`SOURCES.json`](SOURCES.json): upstream provenance and licenses.

## Boundaries

This is one procedural legal-reasoning panel, not evidence for arbitrary legal
workflows or a universal selector. Evaluation episodes, turns, tasks, and
checkpoints are nested observations; they are not independent training
interventions. The result supports the measurement-and-abstention workflow and
identifies where more independent panels are needed.
