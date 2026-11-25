# Hidden-run risk prediction on tau2-bench

This external check asks whether completed customer-support runs identify tasks
at high risk under a held-out model configuration. It uses the original
tau2-bench airline, retail, and telecom result files, with four attempts per
task and model configuration. The predictor assigns one score to each task and
evaluates that score against the four held-out attempt outcomes.

## Result at a glance

The method was selected through eight leave-one-model-out folds on airline and
retail. Across 2,624 held-out attempts, prior runs predicted task-level failure
with 0.787 mean ROC AUC. Required-action count reached 0.594. The highest-risk
20% of tasks contained 40.9% of failures, compared with 24.5% for the
required-action-count baseline.

We then replayed the same rule without opening the o4-mini telecom outcomes.
Three visible model configurations predicted a 42.47% pass rate. The held-out
run achieved 42.11%, an absolute error of 0.37 percentage points. The target
results were already public, so this is an outcome-blind historical replay
rather than a temporally prospective test.

| Frozen telecom result | Value |
| --- | ---: |
| Tasks | 114 |
| Held-out attempts | 456 |
| Failure ROC AUC (task score, attempt outcome) | 0.882 |
| Required-action-count ROC AUC | 0.828 |
| Failure-probability Brier score | 0.137 |
| Constant-rate Brier score | 0.244 |
| Failure precision in highest-risk 20% | 96.7% |

A 5,000-sample task-cluster bootstrap gives a 95% interval of
[0.838, 0.921] for task-level failure AUC. The AUC improvement over
required-action count is [0.001, 0.113]. The absolute Brier-score improvement
over the constant-rate baseline is [0.081, 0.134].

## Study design

The predictor assigns each task its failure frequency across the visible model
runs. It does not use task text, target-model trajectories, or target outcomes.
Required-action count and a constant failure rate are the simple baselines.

Development uses four models in each of the airline and retail domains. Each
model is held out in turn while the other three define task risk. After this
method was fixed, the telecom prediction used Claude 3.7 Sonnet, GPT-4.1, and
GPT-4.1 mini. The o4-mini telecom outcomes remained closed until the prediction
file was serialized with content digest
`625d1dd3dcec4d9082a9eb317054ff7177dc22e8d167c39e6621acda2ac22fca`.

The released airline and retail files predate task corrections introduced in
tau2-bench v1.0.0. This study compares configurations only within that
internally consistent historical release. The telecom tasks are unchanged and
verify in the pinned repository revision.

## Interpretation

Failure patterns transfer across model configurations in these public
customer-support runs. The transfer improves calibrated failure prediction and
task ordering beyond the prespecified simple baselines. The result supports a
low-cost completed-run audit before a new model configuration is opened.

The independent unit is the task. The four attempts per task are repeated
observations, and the bootstrap resamples complete tasks. This remains one
outcome-blind telecom replay after retrospective method development on two
domains.

The benchmark reward is not a complete process-safety signal. A separate
[public tau2-bench audit](https://github.com/sierra-research/tau2-bench/issues/298)
reports reward-passing trajectories that mutated state before obtaining
required confirmation. Process conformance and verifier disagreement therefore
require separate trace checks rather than inference from final reward alone.

## Scope

This study predicts task-level failures in a held-out inference-time model run.
It does not evaluate RL training gains, causal effects of individual tasks, or
candidate-environment selection. The prospective STATE-Bench study in the
parent directory addresses the separate environment-selection question.

## Reproduce

The compact released record is sufficient to reproduce every reported metric.
The reproducer also verifies every released file against the manifest:

```bash
cd experiments/agentic/customer-support-environment-utility/external-checks/tau2-hidden-run-risk
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

To reconstruct the compact record from the pinned upstream checkout:

```bash
python scripts/extract_compact.py /path/to/tau2-bench \
  --output /tmp/compact-outcomes.json
cmp /tmp/compact-outcomes.json data/compact-outcomes.json
```

## Files

- [`PROTOCOL.json`](PROTOCOL.json): development split, frozen target, metrics,
  baselines, and claim boundary
- [`SOURCES.json`](SOURCES.json): source revision, license, sizes, and hashes
- [`data/compact-outcomes.json`](data/compact-outcomes.json): task-level rewards
  and required-action counts derived from the pinned source files
- [`results/DEVELOPMENT_AUDIT.json`](results/DEVELOPMENT_AUDIT.json): eight
  leave-one-model-out folds and compact source receipts
- [`results/FROZEN_PREDICTION.json`](results/FROZEN_PREDICTION.json): serialized
  pre-outcome telecom prediction
- [`results/SCORED_TARGET.json`](results/SCORED_TARGET.json): held-out telecom
  score
- [`results/BOOTSTRAP.json`](results/BOOTSTRAP.json): task-cluster uncertainty
- [`scripts/extract_compact.py`](scripts/extract_compact.py): source-identity
  validation and compact extraction
- [`scripts/reproduce.py`](scripts/reproduce.py): deterministic reconstruction
- [`test_reproduce.py`](test_reproduce.py): scientific-integrity checks
- [`MANIFEST.sha256`](MANIFEST.sha256): released-file hashes
