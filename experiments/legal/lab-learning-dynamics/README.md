# Legal-agent learning dynamics and regression risk

This record asks two related questions about one released continuing-RL legal
agent intervention:

1. How does performance evolve across training rather than only at the final
   checkpoint?
2. Can task information available before continued training flag later
   regressions in a practice area excluded from model fitting?

## Result at a glance

The best aggregate criterion-pass checkpoint occurred before the final
checkpoint. Twenty-seven of 180 tasks later regressed by more than two
percentage points. Task and workflow structure predicted regression risk in
held-out practice areas with 0.648 ROC AUC, compared with 0.425 from
starting-policy behavior alone.

The practical implication is that a legal post-training run can improve in the
aggregate while becoming worse on specific workflows. In this study, task and
workflow information available before continued training identified 37.0% of
the later regressions in the highest-risk 20% of tasks. This supports two
concrete uses: selecting a checkpoint before aggregate performance declines
and prioritizing workflows for regression testing.

This is evidence from one continuing-training intervention. It supports
learning-dynamics and regression-risk analysis, but it does not establish
causal effects for individual training tasks or a new trainer.

## Study design

The intervention starts from `deepseek-ai/DeepSeek-V4-Flash-0731`, uses the
Harvey Legal Agent Benchmark agent loop, and reports the same 180 evaluation
tasks at 15 checkpoints. The tasks span 34 practice areas. Tasks, checkpoints,
criteria, and judge passes are nested observations under one trained
intervention. They are not independent training runs.

The regression endpoint is a task-level criterion-pass decrease greater than
two percentage points between the starting policy and step 70. There are 27
such tasks.

The regression-risk analysis uses leave-one-practice-area-out evaluation. No
task from the held-out practice area enters model fitting or hyperparameter
selection. Static features describe task and workflow structure. They do not
use post-step-zero model responses, rewards, or trajectories.

## Learning dynamics

| Checkpoint | Criterion pass | Change from start | All-pass | Valid ending |
|---:|---:|---:|---:|---:|
| 0 | 82.41% | 0.00 pp | 7.22% | 77.78% |
| 40 | **92.27%** | **+9.85 pp** | 12.22% | 98.33% |
| 65 | 91.48% | +9.06 pp | 15.56% | 95.56% |
| 70 | 89.73% | +7.32 pp | 16.67% | 95.00% |

The best aggregate criterion-pass checkpoint occurs before the final
checkpoint. Overall improvement therefore coexists with non-monotonic learning
and task-level regressions.

At step 65, the paired mean task change is +9.06 points, with a paired-task
bootstrap interval of [5.15, 13.23] points. This is a different analysis from
the step-70 regression endpoint and is reported separately.

## Held-out practice-area results

| Input view | ROC AUC | Average precision | Brier score | Recall in top-risk 20% |
|---|---:|---:|---:|---:|
| Starting-policy behavior | 0.425 | 0.126 | 0.130 | 3.7% |
| Static task/workflow structure | 0.648 | **0.273** | **0.123** | **37.0%** |
| Behavior + static structure | **0.654** | 0.261 | 0.123 | 29.6% |
| Random fingerprint | 0.504 | 0.151 | 0.152 | 14.8% |
| Shuffled static pairing | 0.322 | 0.109 | 0.135 | 3.7% |

For the combined view relative to starting behavior, the practice-area
clustered 95% interval is [0.131, 0.362] for AUC improvement and [0.053, 0.290]
for average-precision improvement.

## Interpretation

Task and workflow structure contains regression-risk signal within this
released intervention, including when the target practice area is excluded
from fitting. This does not show that an individual task caused a regression,
and it does not calibrate risk for a new trainer, model family, or unseen
distribution. Multiple controlled candidate environments are required for
that stronger claim.

## Reproduce the compact record

```bash
cd experiments/legal/lab-learning-dynamics
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The reproducer checks the full checkpoint curve, reported extrema, metric
ordering, negative controls, and claim boundary from compact source-linked
records. It does not redownload or redistribute the upstream task corpus.

## Files

- [`data/checkpoints.json`](data/checkpoints.json): complete 15-checkpoint curve.
- [`data/regression-risk.json`](data/regression-risk.json): compact metrics,
  clustered intervals, endpoint, and support.
- [`results/summary.json`](results/summary.json): released reproduced summary.
- [`SOURCES.json`](SOURCES.json): upstream revisions, licenses, and source hashes.
- [`scripts/reproduce.py`](scripts/reproduce.py): deterministic reconstruction.
- [`test_reproduce.py`](test_reproduce.py): scientific-integrity checks.
- [`MANIFEST.sha256`](MANIFEST.sha256): release-file hashes.
