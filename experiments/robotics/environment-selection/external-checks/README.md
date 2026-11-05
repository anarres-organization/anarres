# External checks for robot-data and reward selection

These records test three qualification hypotheses against downstream robot-policy
outcomes:

1. Policy-responsive data collection should outperform semantic relevance
   alone.
2. Offline trajectory correlation should identify the most useful reward
   model.
3. An opening-state action probe should identify policies at risk of never
   initiating the task.

The first hypothesis receives positive temporal external evidence from GUILD.
The second fails an outcome-blind public shadow test on SOLE-R1. The third
receives positive retrospective evidence from released GreenBall checkpoints.
All three results are retained.

## Results at a glance

| Check | Result | Evidence status |
| --- | --- | --- |
| GreenBall initiation | Selected the better data-processing recipe at all five matched budgets. Rank correlation with physical initiation success was 0.747. | Retrospective, 20 released checkpoints |
| GUILD data collection | Ordered 11 of 12 comparisons correctly with 1.25 percentage points of allocation regret. | Temporal external evidence |
| SOLE-R1 reward selection | The frozen primary rule failed. A false-completion control selected the observed winner. | Retrospective falsification |

Together, these checks support policy-responsive data qualification while
showing that one offline score is insufficient. Physical evaluation remains
the final authority.

## GUILD: positive temporal external evidence

The governing rule predates GUILD and favors policy-relative target transfer
over semantic relevance alone. The paper was released later, but its abstract
exposed the winning direction before the source-specific record was written.
This is therefore temporal external evidence, not a newly prospective test.

The real-robot comparison fixes Octo-Small, trains for 25,000 gradient steps
with a 50/50 target/collected-data mixture, uses matched collection budgets,
and evaluates each method on the same 20 initial configurations for each of
four target tasks.

| Metric | Result |
|---|---:|
| Top-choice accuracy | 3/4 |
| Pairwise ordering versus three baselines | 11/12 |
| Mean allocation regret | 1.25 pp |
| Advantage over semantic-only collection | 23.75 pp |
| Advantage over expert strategies | 15.0 / 20.0 pp |

The miss is important: on `pink-cup-sink`, the selected strategy reached 50%
success while one experienced-human strategy reached 55%.

## SOLE-R1: a failed outcome-blind rule

Before opening the downstream result table, the frozen primary rule selected
the candidate with the highest task-macro trajectory correlation. On the exact
candidate overlap, this selected RoboReward. SOLE-R1 was the downstream winner.

A lower-false-completion control did select SOLE-R1. The failure changes the
measurement contract: offline trajectory correlation is not sufficient when a
reward model can be exploited during optimization. Future qualification must
also measure false-completion suppression, success/failure separation,
policy-relative progress, safety, recovery, reliability, and cost.

This was outcome-blind to the detailed table, but not chronologically
prospective. Baseline checkpoint revisions are only partially identified, and
the real-world policy result has one training seed.

## GreenBall: initiation failure from an opening-state probe

The GreenBall validation study reports that ordinary held-out action error can
miss a dominant physical failure: a policy may never leave its rest pose. We
applied the source-specified opening-state probe to 20 released Diffusion Policy
checkpoints. The panel contains two checkpoints for each combination of five
demonstration budgets and two preprocessing recipes.

The offline measurement uses 25 held-out opening observations per checkpoint.
It records whether any predicted joint moves at least 20 degrees during the
first second. Physical start rates were joined only after these measurements
completed.

| Metric | Result |
| --- | ---: |
| Matched budgets where the probe selected idle trimming | 5/5 |
| Rank correlation with pooled physical start rate | 0.747 |
| Released checkpoints | 20 |

Demonstration count cannot choose between the two recipes because every
comparison is budget matched. The probe recovers a task-initiation failure that
the data-volume baseline cannot represent.

This is one nested scaling study. Physical outcomes are pooled by recipe and
budget, and only two checkpoints are available in each condition. The result
supports an initiation-risk measurement within this policy family. It does not
replace real-robot evaluation or establish a general cross-architecture selector.

## Reproduce

```bash
cd experiments/robotics/environment-selection/external-checks
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The script reconstructs GUILD's selection metrics, verifies that the frozen
SOLE-R1 rule failed without rewriting the prediction, and recomputes the
GreenBall matched-budget decisions and rank correlation.

## Files

- [`data/guild.json`](data/guild.json): four matched real-robot task decisions.
- [`data/sole-r1.json`](data/sole-r1.json): frozen selection and public outcome facts.
- [`data/greenball-initiation.json`](data/greenball-initiation.json): compact
  offline initiation measurements and pooled physical start rates.
- [`data/greenball-checkpoint-panel.json`](data/greenball-checkpoint-panel.json):
  exact model identities and revisions for the 20 measured checkpoints.
- [`results/summary.json`](results/summary.json): released reproduced summary.
- [`SOURCES.json`](SOURCES.json): official source identities and hashes.
- [`scripts/reproduce.py`](scripts/reproduce.py): deterministic scoring.
- [`test_reproduce.py`](test_reproduce.py): chronology and claim-boundary tests.
- [`MANIFEST.sha256`](MANIFEST.sha256): release-file hashes.
