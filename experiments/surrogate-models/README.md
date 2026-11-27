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

### Structured replay result

The grouped structured replay is released in
[`STRUCTURED_REPLAY_RESULTS.json`](STRUCTURED_REPLAY_RESULTS.json). It fits each
model without the held-out study or publication and selects hyperparameters by
grouped validation inside the training fold. Candidate seeds are aggregated
before selection.

Measurements improve substantially over the metadata baseline in the materials
and finance bridges. They do not improve the six-study seed-level suite, where
the methods remain tied. The replay also does not yet charge measurement and
surrogate costs or define an abstention rule. The frozen advancement gate
therefore does not advance this structured predictor to a prospective test. It
does not gate the matched record-conditioned comparison in the accepted
research plan. This is a retrospective result, not evidence against a later
surrogate with richer, properly qualified inputs.

Reproduce the complete fit and score with:

```bash
uv run --group surrogate-test python \
  experiments/surrogate-models/run_structured_replay.py --run
```

The prediction file and fit receipt are written before the scorer opens the
held-out outcome fields.

### Record-conditioned replay

The [record-conditioned protocol](RECORD_CONDITIONED_PROTOCOL.md) implements
the next comparison in the accepted research plan. It holds out complete
studies and separately varies access to cross-study experimental history and
Anarres measurements. A single query ranks every candidate in a matched panel.
Target-study outcomes remain in a protected artifact until predictions are
written and content-addressed.

Matched TF-IDF ridge and nearest-neighbor baselines use the same semantic
records and measurement ablation. Their hyperparameters are selected only
inside each outer training fold. The frozen model, prompt conditions, scoring
rules, and contamination boundary are recorded in
[`RECORD_CONDITIONED_CONTRACT.json`](RECORD_CONDITIONED_CONTRACT.json).

The completed retrospective comparison is released in
[`RECORD_CONDITIONED_RESULTS.json`](RECORD_CONDITIONED_RESULTS.json). All 36
requests completed on their first attempt. The runtime used 233,683 total
tokens and is recorded in
[`RECORD_CONDITIONED_RUNTIME.json`](RECORD_CONDITIONED_RUNTIME.json).

| Condition | Regret | Pairwise ordering | Top-choice credit |
| --- | ---: | ---: | ---: |
| No history, no measurements | 0.187 | 72.6% | 71.4% |
| Cross-study history, no measurements | 0.460 | 65.3% | 20.1% |
| No history, with measurements | **0.182** | **79.9%** | 66.7% |
| Cross-study history, with measurements | 0.325 | 68.3% | 36.1% |
| Best matched text baseline | 0.377 | 69.3% | 33.3% |

Measurements lower the point estimate of regret in both matched comparisons,
but neither six-study cluster-bootstrap interval excludes no improvement. The
best record-conditioned condition also has lower regret than the best matched
text baseline, but its interval includes no improvement. These are promising
point estimates, not a stable cross-study advantage.

Cross-study outcome history makes selection worse. Without measurements, the
regret change is -0.273 in the improvement direction, with a 95% interval of
[-0.532, -0.027]. With measurements, the change is -0.143, with an interval of
[-0.393, 0.030]. The current archive therefore does not support the proposed
benefit from accumulated outcomes. Released native rules are reported
separately because none covers the same nine target panels under the common
scoring contract.

This result does not pass the prospective advancement gate. The archive has
only six independent studies, lacks a common measurement-cost field, and does
not establish calibrated uncertainty or a cost-aware abstention rule. The next
useful step is to add more independent experimental records and qualify a
history representation on development studies before another frozen replay.

Verify the frozen inputs, refit the matched text baselines, and rescore the
content-addressed predictions with:

```bash
uv run --group surrogate-test python \
  experiments/surrogate-models/build_record_conditioned_replay.py --check
uv run --group surrogate-test python \
  experiments/surrogate-models/run_matched_text_baselines.py --run
uv run --group surrogate-test python \
  experiments/surrogate-models/score_record_conditioned_model.py
```

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
5. [Frozen replay suites](REPLAY_SPLITS.json)
6. [Frozen baseline contract](BASELINE_CONTRACT.json)
7. [Released baseline audit](BASELINE_AUDIT.json)
8. [Separated model-input contract](MODEL_INPUT_CONTRACT.md)
9. [Record-conditioned replay](RECORD_CONDITIONED_PROTOCOL.md)
10. [Record-conditioned results](RECORD_CONDITIONED_RESULTS.json)
11. [Multimodal surrogate program](MULTIMODAL_SURROGATE.md)
12. [Mathematics reference fixture](MATHEMATICS_REFERENCE.md)
