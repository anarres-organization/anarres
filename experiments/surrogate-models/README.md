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

### Domain-centered development corpus

The next corpus view is frozen in
[`DOMAIN_SURROGATE_INVENTORY.json`](DOMAIN_SURROGATE_INVENTORY.json). It
prioritizes legal, robotics, materials science, finance, and agentic coding and
keeps mathematics only as a conformance fixture in the first replay. The view
contains 3,713 utility records across 985 native candidate panels. Agentic
coding adds 104 candidate-endpoint records from 14 independent training
decisions; endpoints remain nested under their decision.

The accompanying [protocol](DOMAIN_SURROGATE_PROTOCOL.md) separates candidate
utility from localized regression risk. Legal, robotics, materials science,
and agentic coding expose regression evidence with different independent
units and transfer boundaries. Finance currently lacks released localized
regression labels. The materials predictor's prospectively frozen target-risk
scores achieve 0.494 ROC AUC on 200 candidate-material outcomes, so that miss
is retained rather than folded into a positive cross-domain summary.

The grouped development suites are content-addressed in
[`DOMAIN_SURROGATE_SPLITS.json`](DOMAIN_SURROGATE_SPLITS.json). They are the
place to qualify retrieval, model, uncertainty, and abstention choices before a
new prospective panel is opened. They do not reopen the scored six-study replay
for model selection.

The first structured development replay is released in
[`DOMAIN_STRUCTURED_RESULTS.json`](DOMAIN_STRUCTURED_RESULTS.json). It fits
every method without the held-out study or coding decision and selects its
regularization or tree parameters inside the training fold.

| Development suite | Best method | Pairwise ordering | Normalized regret |
| --- | --- | ---: | ---: |
| Agentic coding | Measurement ridge | 81.5% | 0.053 |
| Finance | Small tree ensemble | 70.8% | 0.235 |
| Materials science | Measurement ridge | 62.3% | 0.323 |
| Controlled legal, robotics, and materials studies | Tie | 50.0% | 0.527 |

The coding, finance, and materials suites contain useful environment-selection
signal. The five-study controlled suite does not yet transfer: every fitted
method remains at the uninformed baseline. These results support domain-aware
development, not a universal cross-domain surrogate claim. The advancement
gate remains closed because costs and abstention are not yet scored and
localized regression calibration is a separate endpoint.

The next record-conditioned comparison is frozen in
[`DOMAIN_RECORD_CONDITIONED_CONTRACT.json`](DOMAIN_RECORD_CONDITIONED_CONTRACT.json).
An outcome-blind hash selects at most two panels per independent study or
coding decision, producing 89 panels across 51 groups. Retrieval selects whole
comparison panels from outside the held-out group and balances same-domain
with cross-domain history. This prevents the 805 materials panels from
dominating the test and prevents retrieval from selecting isolated winners.

The matched text baselines are released in
[`DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json`](DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json).
The best reaches 67.9% study-macro pairwise ordering and 0.274 normalized
regret. These are the minimum semantic baselines for the frozen language-model
comparison.

Inference began under the frozen contract. After 83 valid predictions, one
request exhausted both allowed attempts without final JSON. Before opening any
protected labels, the execution contract was amended to record this case as a
zero-confidence neutral abstention and charge both failed attempts. Successful
request payloads, target panels, retrieval, and scoring remain unchanged.

All 356 requests then completed. The scored study-macro results are:

| Condition | Pairwise ordering | Normalized regret | Top-choice credit | Abstention |
| --- | ---: | ---: | ---: | ---: |
| No history, no measurements | 50.6% | 0.481 | 33.0% | 100.0% |
| Retrieved history, no measurements | 63.6% | 0.326 | 50.1% | 54.9% |
| No history, with measurements | 72.0% | 0.232 | 65.3% | 29.4% |
| Retrieved history, with measurements | **74.3%** | **0.167** | **67.2%** | **11.8%** |

Measurements provide the largest improvement. Adding retrieved history to the
measured target reduces regret by 0.065, with a study-clustered 95% interval of
[0.003, 0.128]. Its 2.3-point ordering improvement has an interval that crosses
zero. The full condition also improves over the fixed TF-IDF baseline: regret
falls from 0.274 to 0.167 and ordering rises from 67.9% to 74.3%. Both paired
intervals exclude zero.

| Domain | Studies | Panels | Pairwise ordering | Normalized regret |
| --- | ---: | ---: | ---: | ---: |
| Agentic coding | 14 | 22 | 81.9% | 0.032 |
| Finance | 16 | 30 | 68.7% | 0.240 |
| Legal | 1 | 1 | 0.0% | 1.000 |
| Materials science | 17 | 33 | 75.5% | 0.157 |
| Robotics | 3 | 3 | 87.2% | 0.185 |

The effect is not uniform. Retrieval lowers regret for coding, finance, and
robotics, but raises regret by 0.035 for materials science. The single legal
study is predicted incorrectly. This result advances record-conditioned models
as a development baseline; it does not establish a general surrogate or justify
prospective allocation.

Rebuild and verify this view with:

```bash
python experiments/surrogate-models/build_domain_surrogate_inventory.py --check
python experiments/surrogate-models/build_domain_surrogate_splits.py --check
python experiments/surrogate-models/build_domain_model_views.py --check
python experiments/surrogate-models/build_domain_record_conditioned_replay.py --check
uv run --group surrogate-test python \
  experiments/surrogate-models/run_domain_structured_replay.py --run
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
11. [Domain-centered protocol](DOMAIN_SURROGATE_PROTOCOL.md)
12. [Domain-centered inventory](DOMAIN_SURROGATE_INVENTORY.json)
13. [Domain-centered grouped splits](DOMAIN_SURROGATE_SPLITS.json)
14. [Domain-centered structured replay](DOMAIN_STRUCTURED_RESULTS.json)
15. [Domain record-conditioned contract](DOMAIN_RECORD_CONDITIONED_CONTRACT.json)
16. [Domain matched text baselines](DOMAIN_MATCHED_TEXT_BASELINE_RESULTS.json)
17. [Multimodal surrogate program](MULTIMODAL_SURROGATE.md)
18. [Mathematics reference fixture](MATHEMATICS_REFERENCE.md)
