# Surrogate models for environment selection

**Status:** research design. No general surrogate model has been validated or
released.

This program asks whether measurements collected before training improve the
selection of candidate environments under a fixed research budget. It builds
on [issue #92](https://github.com/anarres-organization/anarres/issues/92) and
[issue #94](https://github.com/anarres-organization/anarres/issues/94).

The first study is intentionally narrower than a general model of post-training
research. It fixes the starting policy, trainer, target, and training budget
within each candidate panel. A surrogate receives only information available
before a candidate outcome and predicts downstream utility or ranks the
candidates. A selection rule then decides which candidate to train, measure
again, or reject in favor of the starting policy.

The primary question is:

> Do starting-policy measurements reduce allocation regret after their cost is
> included, relative to strong rules using the same experimental history?

## Program stages

### 1. Structured replay benchmark

The first stage evaluates simple predictors and acquisition rules on complete
candidate panels already released by Anarres. Each study keeps its native
target and utility units. Results are aggregated through within-panel ordering,
normalized regret, and cost, not by pooling raw outcome values across domains.

The [replay protocol](REPLAY_PROTOCOL.md) defines the information cutoff,
independent units, splits, baselines, endpoints, and acceptance criteria. The
[source audit](SOURCE_AUDIT.md) records which released studies can support each
comparison.

### 2. Frozen prospective test

Retrospective replay can compare methods cheaply, but it cannot establish that
a selected rule works on a new panel. A later prospective study must freeze the
candidate construction, predictor, allowed updates, acquisition rule, costs,
and scoring before candidate outcomes are available.

### 3. Learned record-conditioned surrogate

A richer model may later use structured recipes, text, code, logs, curves, or
trajectories. Extra inputs are admitted only when their prediction-time
availability is defined and an ablation shows incremental decision value. Raw
numerical curves remain the primary representation when they are available;
rendered plots are not a substitute for the underlying values.

Training a dedicated multimodal model is not part of the first study. Existing
records contain correlated checkpoints, tasks, and repeated evaluations nested
under a much smaller number of interventions. Model complexity should follow a
count of independent interventions and a successful structured baseline.

## Scientific boundaries

- Format compatibility does not establish predictive transfer.
- A task, checkpoint, or evaluation sample is not an independent training
  intervention.
- Outcomes, later checkpoints, post-outcome summaries, and outcome-derived text
  remain outside the surrogate input at prediction time.
- Infrastructure failures remain separate from valid low-utility outcomes.
- Each candidate panel retains its native target and intervention contract.
- Cross-domain conclusions require complete-domain or complete-study holdouts.
- Measurement, surrogate fitting, candidate training, failed execution, and
  evaluation costs are reported separately.
- The option to retain the starting policy is part of the decision problem.

No shared forecast schema or maintained model package is proposed at this
stage. Study-local records should first exercise the lifecycle described in
[RFC 0004](../../docs/rfcs/0004-predictive-decision-records.md).

## Reading order

1. [Literature review](LITERATURE.md)
2. [Released-source audit](SOURCE_AUDIT.md)
3. [First-study replay protocol](REPLAY_PROTOCOL.md)

