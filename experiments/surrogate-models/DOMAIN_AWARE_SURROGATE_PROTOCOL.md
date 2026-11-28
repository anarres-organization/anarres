# Domain-aware surrogate protocol

**Status:** development-selected policy frozen for future, unseen studies. It
has not been prospectively validated.

## Why the next model is domain-aware

The 51-group record-conditioned replay establishes two results. Measurements
made under the starting policy provide the largest improvement, and retrieved
experimental history reduces allocation regret overall. The retrieval effect
is not uniform: it helps agentic coding, finance, and robotics, but hurts
materials science relative to measurements alone. Legal has only one
independent utility study and cannot support a transfer claim.

A single retrieval rule is therefore not the next scientific baseline. The
next comparison separates a transparent routing policy from a learned
candidate model.

## Frozen comparator for unseen studies

[`DOMAIN_AWARE_SURROGATE_CONTRACT.json`](DOMAIN_AWARE_SURROGATE_CONTRACT.json)
freezes the comparator selected from the completed retrospective replay:

| Domain | Prediction condition | Action |
| --- | --- | --- |
| Agentic coding | Starting-policy measurements plus retrieved history | Predict |
| Finance | Starting-policy measurements plus retrieved history | Predict |
| Materials science | Starting-policy measurements without retrieved history | Predict |
| Robotics | Starting-policy measurements plus retrieved history | Predict provisionally |
| Legal | None | Abstain until another independent utility study is available |
| Unseen domain | None | Abstain |

This routing rule was selected after observing the retrospective domain
results. Applying it back to those results would be selection-biased and is
not advancement evidence. Its first valid test is a study whose outcomes were
not available when this contract was written.

Robotics remains provisional because the development result contains only
three independent studies. The route may produce a forecast, but no
robotics-wide transfer claim follows from that forecast.

## Deterministic training view

[`DOMAIN_AWARE_TRAINING_VIEW.json`](DOMAIN_AWARE_TRAINING_VIEW.json) aggregates
the 3,713 released utility rows into 3,665 candidate lineages across 985 native
panels and 51 independent study groups. Inputs and protected labels are stored
separately. Candidate, panel, and study keys in the input artifact are opaque
partition metadata rather than model features.

The first release exposes two declared feature views:

- structured metadata, target metric, prediction-time cost, and native
  measurements
- intervention and decision-context text that a method may compose with the
  structured view

Code, curves, trajectories, and perceptual or structural assets remain marked
unavailable. Later manifests may add them only when the native artifact,
license, transformation, availability time, and reconstruction check are
known.

[`DOMAIN_AWARE_NESTED_SPLITS.json`](DOMAIN_AWARE_NESTED_SPLITS.json) freezes
outer complete-study or complete-domain tests and inner grouped folds for model
selection. The retrieval-history pool is identical to the fitting partition
at every level. A held-out study cannot enter fitting, retrieval, calibration,
or model selection through another record.

## Learned candidate

The learned candidate receives the same prediction-time evidence and must
decide whether to use experimental history. Its utility track predicts
within-panel ordering, allocation regret, native-unit outcomes where
comparable, cost, and an abstain action. Domain identity may be used as a
feature, but domain-specific parameters must be fit without the held-out
study.

Localized regression risk is a separate track. A task, material, or evaluation
stratum remains nested under its parent training intervention and never counts
as an independent environment. Legal, coding, materials, and robotics retain
their native targets and grouped validation. Finance remains unsupported for
localized regression prediction until labels are released.

The first learned comparison must report:

1. utility ordering and allocation regret on complete-study holdouts
2. calibration and discrimination for each supported regression endpoint
3. abstention on unsupported domains and missing required measurements
4. archive construction, measurement, fitting, inference, training, and
   evaluation costs separately
5. a modality ablation before text, code, curves, trajectories, structures, or
   perceptual inputs are retained

## First learned comparison

[`DOMAIN_PAIRWISE_RANKER_CONTRACT.json`](DOMAIN_PAIRWISE_RANKER_CONTRACT.json)
freezes structured and structured-plus-text pairwise rankers before fitting.
Each panel contributes equal total training weight, and every regularization
choice is made inside the frozen inner grouped folds.

The structured ranker improves coding, finance, and materials regret relative
to measurement ridge but is tied on the controlled five-study suite. Text
improves the controlled suite while reducing decision quality in finance and
materials. Neither ranker advances. The result is a development ablation: it
does not yet learn when to use history, expose a qualified abstention action,
or make native-study costs comparable.

The subsequent history-support gate uses the completed measurement-only
forecast and outcome-free retrieval-support features to decide whether to run
the history-conditioned forecast. Under leave-one-study-out replay, it reaches
77.5% ordering and 0.147 normalized regret, compared with 75.9% and 0.155 for
the frozen domain route. The history-benefit ROC AUC is 0.80, and routed
inference uses 466,089 tokens rather than the 697,578 tokens charged by always
retrieving.

This remains development-selected evidence. Coverage falls to 68.5%, selective
regret is worse than the frozen route, and the feature set followed an
outcome-aware feasibility analysis on the same archive. The gate may be frozen
for an unseen study, but it cannot validate itself on this replay.

## Advancement sequence

1. Freeze the transparent domain route before any new study outcome opens.
2. Develop the learned gate and regression models only on released development
   studies, using nested grouped validation for every model choice.
3. Freeze both methods on the same new candidate panels and information cutoff.
4. Execute the real training interventions and protected evaluations.
5. Compare regret, ordering, calibration, abstention, and total research cost.
6. Attempt repeated surrogate-guided selection only after the prospective
   comparison passes its declared gates.

Real execution remains the verifier. Neither a model forecast nor a retrieved
historical analogy is allowed to validate itself.
