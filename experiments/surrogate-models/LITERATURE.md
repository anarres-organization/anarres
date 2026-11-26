# Literature review

This review covers methods that could predict or select post-training
experiments. It distinguishes environment selection from broader recipe search
and separates prediction from sequential acquisition.

## Expensive black-box optimization

[Frazier's Bayesian-optimization tutorial](https://arxiv.org/abs/1807.02811)
defines the standard loop: fit a probabilistic surrogate for an expensive
objective, use its uncertainty in an acquisition function, observe the selected
candidate, and update the model. It also covers noisy, multi-task, constrained,
and multi-fidelity settings. Anarres should score predictive error and the
resulting decision rule.

[Freeze-Thaw Bayesian Optimization](https://arxiv.org/abs/1406.3896) models
partial learning curves and decides which runs to start, pause, or resume.
[Hyperband](https://arxiv.org/abs/1603.06560) treats early stopping as adaptive
resource allocation, while [BOHB](https://arxiv.org/abs/1807.01774) combines
that allocation with model-based candidate selection. These methods motivate a
later study of partial runs. They do not replace the first question of whether
pre-training environment measurements improve a finite-panel choice.

[HPOBench](https://arxiv.org/abs/2109.06716) packages tabular, surrogate, and
containerized multi-fidelity benchmarks so optimizers can be evaluated without
rerunning every expensive job. Anarres can adopt the same separation between a
replay benchmark and a later real execution. Replay findings must remain
identified as retrospective.

[Cost-aware Stopping for Bayesian
Optimization](https://proceedings.mlr.press/v306/xie26c.html) evaluates stopping
through cost-adjusted simple regret and gives stopping rules for cost-aware
acquisition functions. This supports an explicit `retain_starting_policy` or
stop action rather than forcing every replay to spend the full budget.

[PFNs4BO](https://arxiv.org/abs/2305.17535) and
[FT-PFN](https://arxiv.org/abs/2404.16795) show that pretrained Transformers can
serve as fast in-context surrogates. FT-PFN reports accurate single-pass
learning-curve extrapolation and lower inference cost than the neural
surrogates it compares against. These are useful later baselines when Anarres
has enough compatible curves. They do not justify fitting a Transformer to the
current archive by default.

## Transfer across tasks and studies

The [transfer-learning survey for Bayesian
optimization](https://arxiv.org/abs/2302.05927) organizes transfer through
initial designs, search spaces, surrogates, and acquisition functions. For
Anarres, source studies and a target study need explicit identities. A random
record split would test interpolation among related records, not transfer to a
new environment-selection problem.

[Simple Meta-Learning for HPO and CASH Using Performance
Representations](https://arxiv.org/abs/2611.07659) represents a candidate by its
historical performance across prior tasks. A Bayesian ridge model using that
representation matches or improves on specialized meta-learning methods in its
benchmarks at lower complexity and cost. This is a required baseline for a
fixed candidate set when candidate identities recur across panels.

Transfer can also fail through negative transfer or unsupported extrapolation.
Anarres should therefore report complete-study and complete-domain holdouts,
support diagnostics, and abstention rather than a single pooled score.

## Data and environment selection across scale

[DoReMi](https://arxiv.org/abs/2305.10429) uses a proxy model and group-robust
optimization to choose pretraining-domain weights. [RegMix](https://arxiv.org/abs/2407.01492)
fits regression models to many small proxy runs and uses them to select a
large-scale data mixture. Both establish that proxy experiments can guide data
allocation, while also showing that proxy construction and compute are part of
the method.

[DataDecide](https://arxiv.org/abs/2504.11393) provides the strongest warning
against unnecessary complexity. Across controlled pretraining experiments on
25 corpora, rankings from one small model are a strong baseline, and none of
eight tested scaling methods improves the reported compute-decision frontier.
The Anarres benchmark must therefore include direct small-budget rankings and
simple fixed rules alongside learned surrogates.

The Anarres mathematics study supplies another local warning: its compact model
transferred across scale after recalibration, but simple selectors remained
competitive and a new uniform composition fell outside the learned ordering.
Surrogate evaluation must include within-grid prediction, composition shifts,
and support shifts.

## Automated model-development systems

[Research World Models](https://arxiv.org/abs/2610.12235) is the closest learned
comparison. A language model receives experimental records in context and
predicts the outcomes of candidate interventions. Its evaluation contains more
than 2,600 records across nine environments and measures both ranking and
selection regret. An Anarres record-conditioned language-model baseline should
receive the same permitted history as every other method and should be scored
against simpler predictors.

[LM2LM](https://arxiv.org/abs/2610.23344) uses a frozen research world model as
a reward model for proposal generation, then executes selected proposals to
correct distribution shift and surrogate overestimation. It supports a later
closed-loop study, but also shows why a surrogate cannot safely replace real
outcomes indefinitely.

[AutoLLMResearch](https://arxiv.org/abs/2605.11518) studies experiment
configuration across fidelities. [JF-HPO](https://arxiv.org/abs/2606.03073)
jointly uses model scale and training budget as fidelities for LLM RL.
[LLMZero](https://arxiv.org/abs/2606.18388) searches adaptive RL schedules from
checkpoint diagnostics. These systems vary more than the candidate environment
and therefore answer a broader question than the first Anarres study.

[AutoSFT](https://arxiv.org/abs/2610.22194) changes proportions, removes or
repairs examples, and synthesizes data under fixed model, trainer, and budget
comparisons. Its controlled data-action scope is close to a future Anarres
candidate-generation study.

[Athanor](https://arxiv.org/abs/2610.21055) provides frozen evaluation,
decontaminated data, managed execution, and a persistent research record for an
autonomous post-training campaign. These controls are relevant to prospective
evaluation even when the experiment selector is not autonomous.

## Reliability and uncertainty

[Accounting for Variance in Machine Learning
Benchmarks](https://arxiv.org/abs/2103.03098) shows that data sampling,
initialization, and hyperparameter choices can materially change comparisons.
Training seeds estimate within-intervention variability; they do not multiply
the number of independent environment interventions.

[A Sober Look at LLMs for Bayesian Optimization Over
Molecules](https://arxiv.org/abs/2402.05015) evaluates language-model features
inside probabilistic surrogates and cautions that language-model uncertainty is
not automatically suitable for exploration. Any language-model surrogate used
by Anarres needs empirical interval or event calibration. Verbal confidence is
not an uncertainty estimate.

[Bayesian Optimization with Formal Safety Guarantees via Online Conformal
Prediction](https://arxiv.org/abs/2306.17815) studies optimization with a bound
on unsafe trials. The result does not directly establish safe post-training,
but it motivates treating target regressions as constraints or calibrated
events rather than folding them into an undocumented scalar score.

## Consequences for the first Anarres study

The literature supports six design choices:

1. Evaluate selection under cost, not prediction error alone.
2. Compare against random selection, fixed native rules, direct low-fidelity
   rankings, and simple statistical predictors.
3. Keep every nested record with its parent intervention during splitting.
4. Use complete-study or complete-domain holdouts for transfer claims.
5. Separate archive replay from a frozen prospective result.
6. Require incremental value before adding text, code, images, trajectories, or
   a dedicated trained model.

