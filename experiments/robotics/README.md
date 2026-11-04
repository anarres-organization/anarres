# Predictable environment selection for robot learning

Robot-learning datasets can be expensive to collect and expensive to train on.
More data is not always the right data: a useful subset must expose relevant
failures, cover enough of the task, and match the policy and evaluation target.

This program asks a concrete question:

> Can measurements made before training help choose between candidate robot
> datasets while knowing when the evidence is too weak to choose?

The work treats a candidate dataset as an intervention. Comparisons keep the
starting policy, training budget, evaluation episodes, and outcome definition
fixed. Candidate construction cannot read the downstream training outcomes.
The final decision is judged by allocation regret: the performance lost by
choosing a candidate other than the best one observed under the frozen
contract.

## First public evidence release

The [environment-selection release](environment-selection/README.md) contains
two complementary records:

1. A **prospective PushT comparison** in which the decision rule was frozen
   before training outcomes were opened. Three equal-size training subsets were
   compared over three training seeds and 500 closed-loop episodes per seed.
2. A **retrospective three-source bridge** spanning Calibra, CuraEval, and
   Mulligan. It tests whether a small set of interpretable measurements carries
   across robot-learning tasks and policies.

The prospective comparison validates a useful behavior: abstaining between two
plausible candidates retained the eventual best candidate. It does not establish
that one selector is generally superior. The retrospective bridge finds that a
simple practical rule beats an uninformed choice, while a fitted linear model
does not yet add reliable value under held-out-context evaluation.

## What is measured

The current representation keeps the following concepts separate:

- target relevance and policy weakness;
- coverage or diversity of selected experience;
- data-quality correction;
- measurement reliability and missingness;
- exposure, training cost, and evaluation cost;
- native downstream outcomes and guardrails.

Native outcomes are never pooled blindly across tasks. A PushT success rate and
a manipulation-task completion rate remain different endpoints. Cross-source
analysis uses within-panel ordering and normalized regret only after candidate
identities, budgets, policies, and evaluation contracts have been checked.

## Scope

This is early evidence, not a universal robotics law. The prospective record is
one simulated PushT setting. It does not establish transfer across embodiments,
locations, long-horizon tasks, real hardware, or simulation-to-reality shifts.
Those settings require new outcome-blind panels and renewed measurement under
their own starting policies.

Robotics studies share Anarres's identity, measurement, and evaluation
contracts while retaining domain-specific safety, simulator, and hardware
requirements.
