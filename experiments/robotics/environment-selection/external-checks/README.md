# External checks for robot-data and reward selection

These records test two pre-training hypotheses against downstream robot-policy
outcomes:

1. policy-responsive data collection should outperform semantic relevance
   alone; and
2. offline trajectory correlation should identify the most useful reward
   model.

The first hypothesis receives positive temporal external evidence from GUILD.
The second fails an outcome-blind public shadow test on SOLE-R1. Both results
are retained.

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

## Reproduce

```bash
cd experiments/robotics/environment-selection/external-checks
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The script reconstructs GUILD's selection metrics and verifies that the frozen
SOLE-R1 rule failed without rewriting the prediction.

## Files

- [`data/guild.json`](data/guild.json): four matched real-robot task decisions.
- [`data/sole-r1.json`](data/sole-r1.json): frozen selection and public outcome facts.
- [`results/summary.json`](results/summary.json): released reproduced summary.
- [`SOURCES.json`](SOURCES.json): official source identities and hashes.
- [`scripts/reproduce.py`](scripts/reproduce.py): deterministic scoring.
- [`test_reproduce.py`](test_reproduce.py): chronology and claim-boundary tests.
- [`MANIFEST.sha256`](MANIFEST.sha256): release-file hashes.
