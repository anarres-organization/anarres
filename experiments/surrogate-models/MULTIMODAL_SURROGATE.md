# Multimodal surrogate program

**Status:** model and evaluation specification. No trained cross-domain model or prospective result is claimed here.

## Objective

Learn a surrogate that receives a proposed training intervention and the evidence available before its outcome, then forecasts:

- downstream utility on the declared target
- probability and location of regressions
- execution cost and infrastructure-failure risk
- uncertainty, evidence support, and an acquire, select, or abstain decision

The target is not one pooled score across domains. The model produces target-conditional native predictions and decision quantities that can be compared within a candidate panel.

## Experimental record

One record represents one independently executed training intervention. It contains typed references to:

1. **Context:** starting policy, target, trainer, budget, verifier, and time.
2. **Candidate:** environment membership, construction rule, and intervention.
3. **Structured measurements:** starting performance, qualification results, native coordinates, costs, and missingness.
4. **Text:** task and environment descriptions, hypotheses, and notes that predate the outcome.
5. **Code and configuration:** permitted diffs, manifests, trainer contracts, verifier contracts, and dependency identities.
6. **Numeric sequences:** probe summaries, resource traces, and any partial curves explicitly available at the decision point.
7. **Domain-native evidence:** trajectories, tool events, images, video, structures, graphs, or signals when the originating study establishes their meaning.
8. **Outcome:** held-out utility, regression events, cost, validity, and uncertainty, opened only for fitting or scoring under the declared split.

Every field carries provenance and availability time. Missing modalities remain missing rather than receiving invented defaults. Raw artifacts stay linked to their native studies; derived views record their transformation and digest.

## Model ladder

Every method receives the same training records and prediction cutoff:

1. native fixed rules and historical candidate rankings
2. metadata-only ridge or Bayesian-ridge regression
3. metadata plus structured Anarres measurements
4. a small tree ensemble or calibrated Gaussian process where appropriate
5. a frozen record-conditioned language model using permitted text and code
6. structured-plus-text learned representations
7. a multimodal surrogate using the domain-native evidence available in the training fold
8. a dedicated action-conditioned research world model, if the archive supports a prespecified training and validation split

The multimodal model is a primary research target, not an assumption of superiority. Report the incremental decision value and cost of text, code, curves, trajectories, and perceptual inputs separately. A more complex model advances only when it improves complete-study holdouts over the strongest simpler baseline.

## Splits and leakage controls

Tasks, seeds, checkpoints, and repeated evaluations from one candidate lineage stay together. Primary results use complete-study, chronological, model-family, or complete-domain holdouts. Random record splits are diagnostic only.

Exclude outcome-derived summaries, later checkpoints, source labels that reveal the answer, and retrieved records after the cutoff. For pretrained models, report the possibility that public outcomes were present during pretraining. Reconstruction tests must confirm that normalization preserves the native record while identity and outcome shortcuts remain unavailable to the model.

## Evaluation

Report:

- panel- and study-macro allocation regret
- pairwise ordering and rank correlation within candidate panels
- native-unit error for targets that remain comparable
- regression-event calibration, interval coverage, and abstention behavior
- best observed utility as a function of total research cost
- inference latency, model-training cost, and archive-construction cost
- performance on unseen studies, model families, time periods, and domains

The mathematics reference fixture checks evaluator conformance. Scientific claims come from the cross-domain benchmark and a later frozen prospective test.

## Bounded recursive-improvement loop

The proposed loop is:

1. generate candidate environments or training interventions
2. qualify their contracts and collect prediction-time evidence
3. forecast utility, regression risk, cost, and uncertainty
4. select a candidate, acquire more evidence, or abstain
5. execute the real experiment
6. score protected held-out outcomes
7. append the verified record and recalibrate the surrogate

Real execution remains in the loop. Periodic complete-panel audits should test whether selection has narrowed the archive, hidden failures, or increased surrogate overestimation. A system that optimizes only its own forecast has not demonstrated recursive improvement.

## Release gates

1. Publish a read-only inventory of eligible released interventions and missing fields.
2. Freeze the cross-domain benchmark, splits, baseline suite, and cost model.
3. Score structured and record-conditioned baselines.
4. Train and ablate the multimodal surrogate on the frozen benchmark.
5. Freeze a prospective candidate panel and prediction artifact before opening outcomes.
6. Attempt a bounded repeated-selection study only after prospective calibration and regression-risk criteria pass.
