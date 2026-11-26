# Surrogate models for environment selection

**Status:** research design. No general surrogate model has been validated or released.

This program asks whether Anarres can learn from experimental history across domains to forecast how a candidate training environment will affect a model before the full training run. The intended surrogate uses information available before training, including starting-policy measurements and, when scientifically relevant, text, code, curves, trajectories, images, structures, or other domain-native records, to predict improvement, regression risk, cost, and uncertainty.

The program implements the [surrogate-selection proposal](../../docs/research/post-training-surrogate-models.md) and the [multimodal learned-surrogate proposal](../../docs/research/learned-post-training-surrogate-models.md). Its primary question is:

> Can a learned surrogate improve the selection of candidate environments on unseen studies or domains after measurement, model, and execution costs are included?

The long-term role is a pre-execution evidence layer for bounded improvement loops: qualify a proposal, forecast its likely outcomes, select or abstain, execute the chosen experiment, evaluate it on held-out targets, and add the verified record to the archive. The surrogate does not replace real training or held-out evaluation.

## Program stages

### 1. Cross-domain experimental record

The first scientific release begins with a [content-addressed intervention corpus](CORPUS_CONTRACT.md) built from complete, released candidate panels. Its [generated manifest](CORPUS_INVENTORY.json) and [streamable records](CORPUS_RECORDS.jsonl) currently index 101 seed-level interventions and 3,540 explicitly marked published candidate-arm aggregates. Each record preserves its candidate environment, target, prediction-time measurements, outcome, cost status, provenance, and grouping. Native outcomes are not collapsed into a universal score. Transfer is evaluated through within-panel ordering, normalized regret, regression events, calibration, and cost.

The [replay protocol](REPLAY_PROTOCOL.md) defines the cutoff, independent units, splits, baselines, endpoints, and acceptance criteria. The [source audit](SOURCE_AUDIT.md) determines which studies can supply labels. The [mathematics reference](MATHEMATICS_REFERENCE.md) is a conformance fixture for chronology, evaluator behavior, and cost accounting; it is not the headline cross-domain result.

The current inventory supports structured baselines. Raw multimodal assets are
not silently inferred from study summaries; they enter through a later,
licensed artifact manifest with reconstruction and leakage checks.

### 2. Learned multimodal surrogate

The [model program](MULTIMODAL_SURROGATE.md) compares a fixed ladder of structured, record-conditioned, and multimodal predictors under identical information cutoffs. Multimodality is central to the research question, but each modality must earn its place through held-out ablation. The independent unit remains a training intervention, not a task, checkpoint, trace, or evaluation row.

Primary transfer tests hold out complete studies, model families, time periods, or domains. Methods must expose support and uncertainty and may abstain when a candidate lies outside the evidence represented in the archive.

### 3. Frozen prospective test

Replay identifies a candidate method; it does not establish prospective validity. Before new outcomes are opened, freeze the candidate panel, prediction inputs, model artifact, acquisition rule, costs, abstention rule, and scoring contract. Score every candidate needed by the declared comparison, including the option to retain the starting policy.

### 4. Bounded improvement loop

Only after prospective calibration should the surrogate guide repeated proposal selection. Every cycle returns to real execution and protected held-out evaluation. This prevents the archive from becoming a self-confirming record of surrogate-selected outcomes and measures whether the system continues to improve decisions under distribution shift.

## Scientific boundaries

- Format compatibility does not establish predictive transfer.
- A task, checkpoint, trace, or evaluation sample is not an independent training intervention.
- Outcomes, later checkpoints, post-outcome summaries, and outcome-derived text remain outside the surrogate input at prediction time.
- Public text or code may already be encoded by a pretrained model; exposure risk is reported separately from prospective prediction.
- Infrastructure failures remain separate from valid low-utility outcomes.
- Each candidate panel retains its native target and intervention contract.
- Cross-domain conclusions require complete-domain or complete-study holdouts.
- Measurement, surrogate fitting, candidate training, failed execution, and evaluation costs are reported separately.
- The option to retain the starting policy is part of the decision problem.
- A surrogate forecast is evidence for experiment selection, not verification of the resulting model or a replacement for held-out evaluation.

Study-local records should first exercise the lifecycle described in [RFC 0004](../../docs/rfcs/0004-predictive-decision-records.md). A shared public schema should follow demonstrated compatibility across released studies rather than precede it.

## Reading order

1. [Literature review](LITERATURE.md)
2. [Released-source audit](SOURCE_AUDIT.md)
3. [Cross-domain corpus contract](CORPUS_CONTRACT.md)
4. [Cross-domain replay protocol](REPLAY_PROTOCOL.md)
5. [Multimodal surrogate program](MULTIMODAL_SURROGATE.md)
6. [Mathematics reference fixture](MATHEMATICS_REFERENCE.md)
