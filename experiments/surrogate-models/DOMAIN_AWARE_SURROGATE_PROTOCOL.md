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
