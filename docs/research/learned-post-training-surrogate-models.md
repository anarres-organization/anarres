# Learning a multimodal surrogate model from post-training experiments

Status: discussion proposal, 2026-11-24.

[Issue #92](https://github.com/anarres-organization/anarres/issues/92) discusses
Anarres's role in surrogate-based experiment selection. This proposal examines
how to learn a more expressive predictor from experimental records, with
structured and textual inputs as a possible first scope and multimodal inputs
as an extension. The companion framing is in
[PR #91](https://github.com/anarres-organization/anarres/pull/91).

The research question is: **does learning from richer experimental records
improve prediction and experiment selection beyond existing predictors and
strong history-conditioned baselines under a fixed total research budget?**

The immediate contribution is a research design for maintainer review.
Dataset construction, model training, and prospective experiments would each
be scoped separately with explicit ownership and resources.

## Motivation

The mathematics study uses compact predictors with fitted coefficients and
explicit functional forms. Its
[frozen 14B predictor](https://github.com/anarres-organization/anarres/blob/main/experiments/mathematics/environment-utility/scripts/instantiate_14b_forecast.py)
combines model scale, a saturating token-budget term, response cost, and loss
admission. This is already a learned statistical model and provides a useful
baseline. A richer surrogate could learn representations from configurations,
descriptions, code, and measured histories.

Potential benefits to test include:

- **Shared experimental experience:** reusable knowledge from Anarres records
  and traceable contributions by other researchers, including negative results
- **Richer context:** descriptions, code changes, and configurations that
  express differences beyond a small set of predefined scalar features
- **Multimodal evidence:** numerical time series, plots, images, or trajectories
  when these add useful information beyond structured and textual inputs
- **Transfer:** useful predictions with fewer observations in a new setting,
  evaluated separately for new environments, tasks, and model families
- **Evidence-linked explanations:** identified historical comparisons,
  assumptions, and missing information accompanying a numerical forecast
- **Broader decision support:** predictions of downstream utility, regression
  risk, cost, stability, and the value of another measurement

These are hypotheses. A larger model or a richer input interface requires its
own evidence of incremental value.

## Experimental records as training data

The central example is an identified training intervention and its measured
outcome. The target model's original training examples may be relevant input
evidence, while the surrogate's supervision comes from experimental outcomes.

| Record component | Information to preserve |
| --- | --- |
| Starting policy | Model, checkpoint, tokenizer, and harness identities |
| Candidate environment | Native source, revision, membership, and available policy measurements |
| Intervention | Data change, algorithm or loss, hyperparameters, rollout settings, and training budget |
| Observations | Measurements available at the specified prediction time |
| Outcome | Native endpoint, baseline comparison, uncertainty, and evaluator identity |
| Execution | Realized costs, missing usage, infrastructure status, and checkpoint lineage |
| Provenance | Source, producing run, grouping keys, license, and access conditions |

A source audit should identify which fields are available in existing records
and which comparisons they support. Published improvements and failures can
both contribute. Infrastructure failures retain their execution status and
remain separate from valid low-utility outcomes. Missing results and missing
usage retain their missingness.

External records need traceable conditions and outcomes. A paper summary can
provide context, while a reported comparison supports only the estimand and
conditions documented by its source. Duplicate publications, derived recipes,
and checkpoints from one lineage should retain their grouping relationships.

Existing native artifacts and forecast records should be reused where they
fit. A study-local representation can expose gaps before a shared-schema
proposal is justified. The
[predictive decision records RFC](../rfcs/0004-predictive-decision-records.md)
already separates measurements, forecasts, and later decision scores.

## Inputs and prediction time

A first comparison could fix the starting policy, algorithm, target, and
training budget while varying environments. Inputs could combine compatible
measurements with dataset descriptions and a structured training recipe.
Adding code or logs should have a stated scientific purpose and an ablation.

Two prediction times require separate evaluations:

1. **Before candidate training:** use candidate descriptions, available
   starting-policy probes, recipes, and permitted historical experiments.
2. **During candidate training:** additionally use a declared prefix of the
   current run, with a specified checkpoint and observation cutoff.

Final metrics, later checkpoints, and summaries written after the queried
outcome must remain outside the corresponding input. References retrieved for
the model must obey the same cutoff. Describing an arbitrary experiment in
text extends the input interface; reliable prediction still depends on
training coverage and measured support.

Possible later modalities include learning curves, images of published
figures, example outputs, and robotic trajectories. Preserve raw numerical
curves when available and compare their value with image representations.
Each modality needs a defined encoding, availability rule, acquisition cost,
and test of whether it improves decisions.

## Candidate modeling approaches

| Approach | Possible contribution | Main comparison question |
| --- | --- | --- |
| Record-conditioned language model | Interpret descriptions and code, use retrieved history, and generate explanations | How much does permitted history improve a frozen model? |
| Dedicated trained surrogate | Learn reusable representations and numerical or probabilistic outputs from experiment records | Does training improve transfer or reduce inference cost enough to repay its cost? |
| Typed decision model | Return candidate preferences, utility categories, or event probabilities in a fixed contract | Are outputs useful and calibrated for the declared decisions? |
| Action-conditioned research world model | Predict outcomes or subsequent training state given a proposed intervention | Do its forecasts improve sequential decisions, including after policy changes? |

These approaches can share components. A language backbone could supply a
representation to numerical prediction heads and an optional explanation
decoder. A world-model objective specifies what consequences to predict and
can use different model architectures. The proposal leaves model size and
training method open until data availability and baselines are assessed.

[Research World Models](https://arxiv.org/abs/2610.12235) studies a frozen LLM
using experimental records in context to predict intervention gains. It is a
direct baseline, and its discussion proposes training dedicated models on
research data. [PFNs4BO](https://arxiv.org/abs/2305.17535) provides an earlier
example of pretrained Transformers serving as Bayesian-optimization surrogates.

[Jev's interface](https://docs.typesafe.ai/introduction) illustrates typed
questions and probability outputs. Its
[confidence documentation](https://docs.typesafe.ai/confidence) distinguishes
probabilities from a confidence statistic derived from their distribution.
Either output requires task-specific validation before it guides training
allocation. The interface alone establishes no post-training forecasting
accuracy.

## Outputs and explanations

Downstream utility remains the change in an identified target after a training
intervention. Additional outputs could include utility intervals, candidate
preferences, regression-event probabilities, execution cost, or a stability
endpoint. Each needs a native definition and an evaluable label.

A language-model-based predictor could also identify relevant experiments,
state assumptions, describe missing evidence, or recommend another measurement.
Explanations should cite permitted record identities and distinguish observed
comparisons from hypotheses. Prediction accuracy, explanation support, and
causal attribution require separate evaluation. Verbal confidence and generated
probability values require empirical calibration.

An action-conditioned model could eventually forecast the consequences of
continuing training, changing a parameter, or switching data. Multi-step
planning would need checks for compounding prediction error and periodic
comparison with real outcomes. [LM2LM](https://arxiv.org/abs/2610.23344)
illustrates calibration with executed proposals when surrogate feedback guides
learning. Its evaluated scope is LM development, with post-training an
extension left for future work.

## Evaluation design

The first design should compare the existing parametric predictor, a suitable
conventional surrogate, a frozen LLM using the same permitted history, and any
dedicated trained predictor. Record retrieval is part of the method. Include
structured-only, structured-plus-text, and any multimodal ablations with
matched information boundaries and accounted acquisition costs.

Split records according to the transfer claim. Related checkpoints, repeated
evaluations, and seeds from one intervention must retain their parent
grouping. Hold out source families, research projects, or model families where
appropriate, and add chronological evaluation for later unseen experiments.
Check whether public outcomes could already be known to the backbone model.
Report archive replay separately from prospective prediction.

Evaluation should cover:

1. **Forecasting:** native-unit error, ordering, interval coverage, event
   calibration, and support or abstention behavior.
2. **Selection:** allocation regret and best validated utility over total
   research cost, including the option to retain the incumbent.
3. **Explanations:** accuracy of cited evidence, support for stated comparisons,
   and stability under equivalent descriptions.
4. **Economics:** data acquisition, surrogate training, inference, measurement,
   candidate training, failures, and independent final evaluation.

Report upfront corpus and training costs separately from marginal use on a
new task. Test whether more records or modalities improve prediction at the
same decision budget. A prospective test would freeze the data boundary,
predictor specification and update rule, allowed feedback, acquisition policy,
and scoring before claim-bearing outcomes become available.

## Questions for maintainer review

1. Which prediction target and existing records provide a credible first scope?
2. Should the first comparison use a pretrained model conditioned on retrieved
   records, a dedicated trained predictor, or both?
3. What evidence would justify extra model complexity, modalities, and cost
   beyond existing predictors and history-conditioned LLMs?

The next decision is whether to adopt this research question and document a
bounded first comparison, or record the reason to defer it. Execution can then
be proposed with specific owners, data, compute, and acceptance criteria.
