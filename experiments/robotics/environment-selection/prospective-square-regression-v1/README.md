# Prospective environment and regression prediction on RoboMimic Square

**Status:** complete prospective comparison. The outcome-blind release gate
passed for all 15 candidate policies and 3,840 candidate evaluation episodes.
The frozen aggregate choice led the five equal-size candidate subsets. The
frozen regression-risk prediction failed in the opposite direction.

This study asks whether measurements from a reference robot policy can select
a useful demonstration environment and identify where a trained policy may
regress. It uses the official 300-demonstration RoboMimic Square multi-human
v1.4.1 dataset and the Diffusion Policy contract released with CuraEval.

The experiment first creates a fixed bank of 128 simulator initial states. Three
all-data probe policies estimate which states remain difficult. Those outcomes
are measurement inputs, not candidate-policy outcomes. Candidate construction
then combines the measured failure map with geometric coverage of the same
initial-state distribution. Every unopened candidate is trained from scratch for
the same number of optimizer steps and evaluated on the identical state bank.

## Candidate panel

The panel contains random and shortest-trajectory baselines, an unweighted
coverage subset, a failure-weighted coverage subset, and a failure-weighted
coverage subset restricted to relatively short demonstrations. Coverage
selection retains 50 demonstrations from each of the better, okay, and worse
operator tiers. The all-data probe policies provide a reference surface but are
not presented as unopened candidate outcomes.

The frozen point prediction selects `failure_coverage_short_50`. The aggregate
test measures its success rate and allocation regret. The regression test asks
whether the product of starting-policy failure probability and candidate
coverage distance predicts candidate-minus-reference changes across eight
predefined initial-state strata.

The probe gate qualified with 616 successes and 152 failures across 768 fixed-
state episodes, all eight strata populated, and no simulator exceptions.
[`PROBE_MEASUREMENTS.json`](PROBE_MEASUREMENTS.json) records this measurement,
while [`CANDIDATES.json`](CANDIDATES.json) fixes the six candidate/reference
memberships and state-level regression-risk predictions.

## Why this test is separate from the Can release

The completed Can comparison has success rates between 93.8% and 98.8%. Its
frozen choice beats random selection but does not beat the shortest subset.
Square provides a less saturated setting and a new outcome: paired performance
on fixed initial states rather than aggregate success alone. The protocol also
reports the cost of training and evaluating the probe policies instead of
treating measurement as free.

[`PROTOCOL.json`](PROTOCOL.json) fixes the chronology, candidates, prediction,
training budget, state-bank construction, and scoring rules. [`SOURCES.json`](SOURCES.json)
records the source revisions and dataset identity. [`FREEZE.json`](FREEZE.json)
binds both records to the released fixed-state bank.
[`SCORING_CONTRACT.json`](SCORING_CONTRACT.json) fixes the candidate-by-stratum
regression test, allocation regret, whole-policy bootstrap, and integrity gate.
Scripts in this directory materialize candidate memberships and the sealed
execution matrix without opening candidate outcomes. The generated
`EXECUTION_FREEZE.json` binds qualified memberships to all 15 candidate runs
before candidate training begins. After execution, `gate_candidate_results.py`
checks the complete run matrix, task identities, artifact hashes, evaluation
coverage, and simulator exceptions before any candidate outcome is scored.

## Prospective result

The frozen `failure_coverage_short_50` choice reached 76.30% mean closed-loop
success. It was the strongest of the five 150-demonstration candidates, beating
the fixed random subset by 9.77 percentage points. The shortest-trajectory
baseline reached 75.91%, leaving only a 0.39-point difference between the two
strongest half-data choices. Their ordering is not resolved by three training
seeds.

| Candidate | Demonstrations | Mean success |
| --- | ---: | ---: |
| All-data reference | 300 | **80.21%** |
| Random 50% | 150 | 66.54% |
| Shortest 50% | 150 | 75.91% |
| Coverage 50% | 150 | 73.05% |
| Failure-weighted coverage 50% | 150 | 72.92% |
| Failure-weighted coverage and short 50% | 150 | **76.30%** |

The all-data reference remained 3.91 points higher than the frozen choice. The
whole-policy bootstrap interval for this allocation regret is 0.78 to 7.03
points. The result supports prospective selection among equal-size subsets in
this panel, while the simple length baseline remains competitive and all-data
training remains strongest.

Measurement required three additional all-data probe policies and 768 probe
episodes before candidate construction. The candidate comparison then trained
15 policies and evaluated 3,840 episodes. This cost is part of the selection
procedure and must be charged when comparing it with simpler rules.

The preregistered regression prediction did not transfer. Frozen risk was
expected to correlate negatively with candidate-minus-reference success
changes. The observed Spearman correlation was instead 0.322, with a 95%
whole-policy bootstrap interval from 0.129 to 0.469. The highest-risk quarter
improved by 7.05 points more than the lowest-risk quarter, also opposite the
predicted direction. Starting-policy failure and geometric distance are
therefore insufficient for predicting where a candidate policy will regress in
this setting.

[`RELEASE_GATE.json`](RELEASE_GATE.json) records the sealed completeness and
identity audit. [`RESULTS.json`](RESULTS.json) contains the scored comparison,
and [`evaluations/`](evaluations/) contains the 18 compact fixed-state outcome
records. Recompute the complete result with:

```bash
python scripts/reproduce_released_results.py --output /tmp/square-results.json
python -m unittest test_released_results.py
```

Verify the outcome-blind freeze with:

```bash
python scripts/verify_freeze.py
python -m unittest discover -p 'test_*.py'
```

## Scope

This is one simulated manipulation task, one policy family, three training
seeds per arm, and one fixed training budget. The initial-state representation
uses square-nut pose and is specific to this simulator contract. The aggregate
result supports prospective selection within the frozen half-data panel. The
failed regression test rules out the current risk construction as a reliable
predictor of state-stratum regressions. Neither result establishes a general
robotics allocator.
