# Anarres as a surrogate model for automated post-training experiments

Status: discussion proposal, 2026-11-24.

Anarres measures candidate environments before committing a full training
budget. From an AutoML perspective, those measurements could supply features
and evidence for a surrogate model of downstream training utility. An
acquisition rule could then use the surrogate to choose the next experiment.
This perspective connects predictable post-training to sequential experimental
design and Bayesian optimization.

The proposed research question is: **do Anarres measurements improve experiment
selection under a fixed total research budget, beyond strong surrogates and
search methods using the same available history?**

This document proposes a framing and evaluation criteria for discussion. The
immediate deliverable is agreement on scope, prediction targets, and evidence
needed for a later study. Implementation and training campaigns would each
need a separately scoped contribution.

## Mapping Anarres to surrogate-based optimization

Bayesian optimization models an expensive objective and uses predictive
uncertainty to select evaluations through an acquisition function
([Frazier, 2018](https://arxiv.org/abs/1807.02811)). The corresponding
post-training objects could be:

| Optimization concept | Post-training interpretation |
| --- | --- |
| Context | Starting policy, public target description, evaluator identity, and runtime contract |
| Candidate | Training environment, with a pinned recipe and training budget |
| Expensive objective | Downstream utility measured after training and independent evaluation |
| Surrogate inputs | Candidate metadata, compatible policy measurements, and available experiment history |
| Predictive output | Expected utility, uncertainty, support, and optionally task-level regression risk |
| Acquisition rule | Choice of the next experiment or measurement, accounting for cost and uncertainty |
| Observation archive | Identified training interventions, native outcomes, failures, costs, and checkpoint lineage |

The current CLI supplies qualification, measurement, compatibility, and
evidence preservation. Domain studies provide particular forecasts and
decision rules. A validated, general surrogate and sequential optimizer remain
research questions. The distinction between profiles and forecasts is already
explicit in [predictive decision records](../rfcs/0004-predictive-decision-records.md).

The mathematics study records 32 Qwen3 training trajectories under a fixed
NeMo GRPO contract. Its configurations reference an external training runtime
and checkpoint artifacts. Those records are one possible starting point for a
surrogate comparison. Reusing the training launch and result-collection path
would need a separate assessment of available dependencies and artifacts.

The repository also contains acquisition studies. The
[antibody panel](https://github.com/anarres-organization/anarres/tree/main/experiments/ai-for-science/molecular-design/prospective-antibody-acquisition)
compares acquisition strategies under a common surrogate and label budget.
There the surrogate predicts assay outcomes. Here the proposed surrogate
predicts the utility of a model-training intervention. These are different
levels of experimental design, with useful shared methodology.

## Define the prediction target before choosing a model

A first study could fix the starting policy, target, trainer, algorithm, and
training budget, and vary only the candidate environment. For each candidate,
the label would be:

```text
downstream utility = target performance after training
                   - target performance of the starting policy
```

The label needs an identified intervention arm and evaluator contract.
Repeated evaluation samples are nested under that arm. Independent training
seeds and independent search campaigns answer different uncertainty questions.
Protected evaluation examples and outcomes remain outside search feedback.

A broader recipe could later include data mixtures, learning rate, KL
coefficient, rollout settings, loss, and starting checkpoint. Recipe changes
would then become explicit surrogate inputs. A sequential controller would
also need the current checkpoint and training history as state. Initial
environment selection and control during training should have separate claims.

Policies and loss definitions matter. Usable signal density and effective
coverage are measurements under a specific policy and measurement contract.
Changing advantage normalization or loss admission can change their meaning.
Effective prompt coverage also has a distinct meaning from semantic diversity.
Compatibility should be established before using these coordinates together.
See [domain adapters](../architecture/domain-adapters.md).

Each target retains its native units. Cross-domain transfer would require an
explicit validation argument. A shared record format alone establishes no
common utility scale or transfer law.

## Prediction quality and decision quality

An accurate surrogate could save expensive trials by identifying promising
candidates, warning about regressions, and deciding where another measurement
would be useful. Its practical value depends on the decisions it supports.

Low average prediction error can coexist with a wrong ranking near the best
candidates. Conversely, a surrogate can make useful choices while predicting
absolute scores imperfectly. An acquisition rule may also favor an uncertain
candidate to learn about an unexplored region. The evaluation should therefore
cover three properties:

1. **Prediction:** utility error, ordering, interval coverage, and regression
   calibration on explicitly held-out units.
2. **Selection:** allocation regret within a comparable panel, best observed
   utility as a function of total research cost, and cost to reach a fixed
   utility threshold.
3. **Reliability:** unsupported-region detection, abstention, and calibration
   after the selection process changes the candidate distribution.

Uncertainty should distinguish variability in training and evaluation from
limited knowledge about untested candidates. Gaussian processes, ensembles,
parametric learning curves, and record-conditioned LLMs are possible model
families. Each would need empirical calibration in its claimed setting.

Abstention can mean retaining the incumbent or requesting another measurement.
Its rule should account for the cost of waiting and the consequences of a
regression. A small predicted difference need not justify a confident ranking.

## Sequential and multi-fidelity decisions

A minimal starting point is selecting one environment from a finite panel.
Further decisions could include selecting a short training trial, allocating
more compute to a checkpoint, or collecting another policy probe.

[Freeze-Thaw Bayesian Optimization](https://arxiv.org/abs/1406.3896) uses
partial learning curves to choose between starting and resuming runs.
[BOHB](https://arxiv.org/abs/1807.01774) combines model-based configuration
selection with budget allocation. For LLM RL,
[JF-HPO](https://arxiv.org/abs/2606.03073) uses model size and training budget
as joint fidelities. These provide relevant methods and baselines.

Small models, short runs, reduced datasets, and probes can have different
candidate rankings from full training. The relation between fidelities must be
tested. Feature acquisition also has a cost: a policy probe is an additional
measurement, whereas a short training trial updates weights. Both should be
identified separately in the experiment record.

Costs include source qualification, probes, data preparation, successful and
failed training trials, rollouts, validation, final evaluation, and controller
inference. Report archive-construction and surrogate-fitting cost separately
from marginal cost on a new task. Missing usage remains unknown. Wall time and
accelerator time retain separate units.

## A bounded validation plan

The following stages describe possible evidence, with execution scoped later.

1. **Audit released records.** Identify comparable candidate panels, actual
   training outcomes, independent units, and available costs. Preserve which
   outcomes were already visible to the researcher.
2. **Evaluate retrospective prediction.** Split by environment, source family,
   model, or task according to the transfer claim. Fit and calibrate using
   development records. Keep correlated checkpoints within their parent unit.
3. **Evaluate sequential selection on a fixed archive.** Give methods the same
   initial observations, candidate availability, and budget. Reveal outcomes
   only when selected. Report candidate-pool and replay limitations.
4. **Design a prospective test.** Freeze the predictor specification and update
   rule, acquisition policy, allowed feedback, budget, candidate construction,
   and scoring before new claim-bearing outcomes are available. Posterior
   updates or refits can then use permitted observations, with the model state
   recorded before each decision. A frozen adaptive policy can still change its
   actions in response to that feedback.

Baseline comparisons should include a strong fixed recipe, random selection,
an established surrogate-based or multi-fidelity optimizer, and an LLM using
the same permitted history. For a finite panel, include strong native selection
rules. An ablation should compare metadata and history alone with the same
predictor augmented by Anarres measurements, charging measurement cost.

The central comparison is the incremental decision value of those measurements.
If the comparison finds no gain, that result should narrow the claimed use
case. Released prediction misses and abstentions provide important evidence
about applicability, including the
[mathematics mixture-transfer limit](https://github.com/anarres-organization/anarres/tree/main/experiments/mathematics/environment-utility).

## Relationship to automated post-training research

Recent systems demonstrate different parts of the surrounding loop:

- [AutoSFT](https://arxiv.org/abs/2610.22194) searches data interventions under
  controlled training comparisons.
- [LLMZero](https://arxiv.org/abs/2606.18388) searches adaptive GRPO trajectories
  through checkpoint branching and coordinated parameter changes.
- [AutoRL](https://arxiv.org/abs/2611.17790) monitors and intervenes during an
  ongoing RL run.
- [Athanor](https://arxiv.org/abs/2610.21055) studies a complete autonomous
  post-training campaign with a protected evaluation suite.

[Research World Models](https://arxiv.org/abs/2610.12235) is especially close
to the proposed predictive layer: a frozen LLM uses experiment records to
predict intervention gains. Its record-conditioned predictor is an important
comparison for a measurement-informed surrogate.
[AutoLLMResearch](https://arxiv.org/abs/2605.11518) studies learned configuration
selection across fidelities using a precomputed experimental environment.
[LM2LM](https://arxiv.org/abs/2610.23344) trains proposal generation using
surrogate rewards and periodically executes proposals to recalibrate feedback.
Its evaluated scope is LM development, with post-training an extension left
for future work. It illustrates why adaptive search needs checks against
surrogate overestimation.

Anarres could contribute a tested account of when native environment
measurements improve such prediction and selection. Candidate generation,
prediction, acquisition, and execution can then be evaluated as distinct
components of an automated post-training loop.

## Questions for maintainer review

1. Is environment selection under a fixed recipe the right initial scope for
   this framing, with joint recipe search a later extension?
2. Which released study provides the clearest records for a first surrogate
   comparison, and what independent unit should define its held-out split?
3. Which baseline, uncertainty criterion, and cost endpoint would make a
   positive or negative result useful to the project?
4. Can the study-local forecast and decision records proposed in RFC 0004
   support the comparison before any shared schema is considered?

The proposed next decision is whether to adopt this framing and select a
bounded study question. Subsequent implementation and experiments can then be
proposed with explicit ownership and resources.
