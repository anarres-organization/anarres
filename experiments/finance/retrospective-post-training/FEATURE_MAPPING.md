# Frozen semantic mapping for the expanded finance bridge

This mapping translates source-reported treatment properties into a shared
representation. New sources are encoded from their intervention contracts
before they are added to the grouped rescore. Scores are not numerical inputs
to feature construction, although every result in this audit was already public.

The versioned practical rule and its weights are fixed before each grouped
rescore. It rewards
target alignment, explicit quality and retention controls, verifier or
policy-relative selection, source diversity, human-labeled data, and the two
independently randomized processing stages. The second mapping version adds
context progression after the FinLCR source audit and before its grouped
rescore. Later source additions retain the same coordinate definitions and
practical-rule weights. All outcomes remain retrospective and public. Missing measurements
contribute no weight and remain distinguishable through their observation flags
in the fitted model.

The shared coordinates are:

- target alignment: the reported fraction of examples drawn from the
  evaluation target, or one minus an explicitly reported out-of-domain mix.
- data volume: the within-panel rank of reported example count or data
  fraction.
- source diversity: the within-panel rank of reported source count.
- human-labeled fraction: the reported real-data share in real/synthetic
  mixtures.
- quality control: explicit reasoning distillation, filtering, refinement, or
  a source-defined quality-control treatment.
- retention control: self-distillation, parameter merging, or another explicit
  mechanism designed to preserve the starting policy.
- verifier alignment: finance-specific process selection, compact verifiers,
  or a source-defined verifier-alignment treatment.
- policy-relative selection: hard-example, difficulty-aware, or
  policy-conditioned selection.
- domain-specific selection: a finance-specific selector rather than a
  general selector.
- transcript refinement and QA refinement: the two independently randomized
  stages in the speech-to-SFT factorial study.
- feedback locality: localized correction rather than full-solution or
  reference-only supervision.
- efficient rollout: a source-defined short rollout or answer contract.
- curriculum progression: an explicit sequence from short-context reasoning to
  long-context retrieval, rather than an unordered mixture.

An exploratory compact ridge averages these fields into seven broader concepts:
target fit, curation, retention, verification and policy-relative selection,
source breadth, data volume, and rollout efficiency. This compression is
reported separately from the original full-feature ridge and the fixed
practical decision rule.

Every coordinate is paired with an observation flag. Unreported properties
remain missing rather than being imputed as absent. Starting-policy controls
are coded as observed zeros only for intervention coordinates that are varied
inside their panel.

Categorical method names, study identity, model identity, target identity, and
arm labels are excluded from the predictive representation. Stable random
fingerprints and shuffled outcomes are evaluated only as negative controls.

Outcomes are converted to zero-to-one utility within each source-native panel.
This preserves candidate ordering and normalized regret without treating a
point on one benchmark as numerically equivalent to a point on another.
