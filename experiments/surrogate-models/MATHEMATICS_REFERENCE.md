# Mathematics reference fixture

**Status:** fixed retrospective comparison over released records. This analysis
replays a forecast that was prospectively frozen in the originating study; it
does not create a new prospective result.

This fixture operationalizes the bounded study proposed in
[issue #92](https://github.com/anarres-organization/anarres/issues/92) and its
[companion proposal](https://github.com/anarres-organization/anarres/pull/91).
It uses the [mathematics environment-utility
study](../mathematics/environment-utility/) because that study holds the
trainer, verifier, evaluation target, and warm-start recipe fixed within each
model scale. It also preserves a pre-outcome 14B forecast and its later score.

## Question

Given the Qwen3-14B starting policy, four policy-relative candidate
environments, and a generated-token budget, do starting-policy measurements
improve candidate selection beyond simpler rules fitted on the 1.7B, 4B, and
8B records?

## Prediction target

The target is downstream utility in held-out pass@1 percentage points relative
to the 14B starting policy. The released 14B score contains 12 candidate-budget
means: four candidate environments evaluated at three generated-token budgets.
The two training seeds are replicates within each candidate. Checkpoints are
repeated budget observations from the same trajectory.

The candidate decision is evaluated separately at each budget. Curve error is
diagnostic because the candidate-budget values are not 12 independent training
interventions.

## Permitted fit data

The primary replay uses only records from the 1.7B, 4B, and 8B studies that were
available to the frozen 14B predictor. Permitted fields include:

- model scale and generated-token budget
- candidate identity and construction factors
- starting-policy success
- raw group mixedness
- admission rate and generated-response length
- usable signal density and effective coverage
- earlier-scale candidate outcomes and recorded costs

The 14B starting-policy measurements may be used because they precede 14B
candidate training. The 14B trained-policy outcomes, their summaries, and the
uniform-mixture outcome remain unavailable until scoring.

The existing freeze artifacts are the authority for chronology. The replay
must reproduce their digests before fitting or scoring.

## Methods

The comparison includes:

1. retain the 14B starting policy
2. random candidate selection
3. fixed candidate identity selected using earlier scales
4. the released crossover rule
5. budget and model scale only
6. starting success only
7. raw group mixedness only
8. usable signal density only
9. effective coverage only
10. the released usable-signal-density and effective-coverage model
11. regularized linear models using the same permitted fields
12. a conventional probabilistic surrogate when its fit is numerically stable

A frozen language model receiving the same permitted records is an exploratory
baseline from the proposal. Public 14B results may already be present in
the model's pretraining or retrieval corpus, so this baseline cannot establish
prospective prediction. Its prompts, retrieved records, model identity, and
sampling settings must be released for inspection.

Every learned method fits its preprocessing, regularization, feature selection,
and calibration using only earlier-scale records. The fixed-identity and
crossover rules follow the same information boundary.

## Measurements ablation

The central comparison adds information in four steps:

1. budget and model scale
2. budget, scale, and starting success
3. budget, scale, and raw mixedness
4. budget, scale, usable signal density, and effective coverage

Additional metadata models remain secondary. Each step reports the probe tokens
and verifier calls required to produce its inputs. The study should state the
decision both before and after those costs are charged.

## Primary endpoints

- mean allocation regret over the three 14B budget decisions
- pairwise candidate-ordering accuracy at each budget
- selection of a candidate that regresses relative to the starting policy
- utility of the selected candidate after charging measurement cost

## Secondary endpoints

- curve RMSE and MAE over the 12 candidate-budget means
- interval coverage and width where a method returns intervals
- maximum allocation regret
- decision stability across the two training-seed outcomes
- abstention under a threshold calibrated on earlier scales

The candidate-budget means receive equal weight for curve error. Uncertainty
and hypothesis tests cluster by candidate trajectory. Seed-level results remain
visible and do not become additional candidate panels.

## Robustness analyses

After the fixed 14B replay is scored, run:

- leave-one-scale-out evaluation across all four scales
- leave-one-candidate-environment-out evaluation within the constructed grid
- the released uniform-mixture stress test as a separate composition-shift
  result
- sensitivity to omitting starting success, raw mixedness, usable signal
  density, or effective coverage
- cost sensitivity using probe tokens, candidate-training tokens, and missing
  cost markers separately

The uniform mixture must not be pooled into the controlled four-candidate grid.
It tests a different transfer question and already documents a failure of the
learned ordering.

## Interpretation

This fixture answers whether Anarres measurements add decision value in one
controlled scale-transfer setting. Its program role is to validate the replay
implementation, information boundaries, and baseline suite. It cannot
establish a universal surrogate, cross-domain transfer, or multimodal-model
advantage.

The primary benchmark applies the same evaluator to complete panels that pass
the [source audit](SOURCE_AUDIT.md). A frozen prospective experiment follows
only if improvement survives complete-study holdouts and total-cost accounting.

