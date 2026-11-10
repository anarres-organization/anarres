# Predictable environment selection for robot learning

Robot-learning datasets can be expensive to collect and expensive to train on.
A useful subset must expose relevant failures, cover enough of the task, and
match the policy and evaluation target.

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
three records with complementary designs:

1. A **prospective PushT comparison** in which the decision rule was frozen
   before training outcomes were opened. Three equal-size training subsets were
   compared over three training seeds and 500 closed-loop episodes per seed.
2. A **retrospective three-source analysis** spanning Calibra, CuraEval, and
   Mulligan. It tests whether a small set of interpretable measurements carries
   across robot-learning tasks and policies.
3. A **prospective RoboMimic Can comparison** with five candidate datasets,
   five paired training seeds, and a completeness gate covering 2,500
   evaluation episodes.

The PushT comparison validates a useful behavior: abstaining between two
plausible candidates retained the eventual best candidate. It does not establish
that one selector is generally superior. The retrospective analysis finds that a
simple practical rule beats an uninformed choice, while a fitted linear model
does not yet add reliable value under held-out-context evaluation.

The corrected [prospective closed-loop curation
panel](environment-selection/prospective-cupid-can-v141/README.md) compares one
frozen recommendation with full-data, random, length-based, and unconstrained
influence controls. The shortest-demonstration subset reached 98.8% mean
success, while the tier-balanced CUPID prediction reached 97.4%, for 1.4 points
of allocation regret. All structured choices outperformed the random subset.
The domain adapter reproduces the released score, prepares the exact candidate
masks, binds the 25-run matrix to local or Slurm execution, and verifies every
checkpoint and evaluation log before scoring.

## What is measured

The current representation keeps the following concepts separate:

- target relevance and policy weakness
- coverage or diversity of selected experience
- data-quality correction
- measurement reliability and missingness
- exposure, training cost, and evaluation cost
- native downstream outcomes and guardrails.

Native outcomes are never pooled blindly across tasks. A PushT success rate and
a manipulation-task completion rate remain different endpoints. Cross-source
analysis uses within-panel ordering and normalized regret only after candidate
identities, budgets, policies, and evaluation contracts have been checked.

## External mechanism evidence

The external-checks record now includes an opening-state initiation probe over
20 released Diffusion Policy checkpoints. In five budget-matched comparisons,
the probe selected the idle-trimmed data recipe that had the higher physical
start rate. The offline score and pooled physical start rate had rank
correlation 0.747 across ten recipe-by-budget conditions.

The result is specific to one policy family and one task. It shows why
policy-specific failure measurements can matter more than data volume or
ordinary held-out action error.

## Scope

The prospective evidence comes from one simulated PushT setting. External
records now include physical robot outcomes, but they remain retrospective or
temporally external. Transfer across embodiments, locations, long-horizon
tasks, or simulation-to-reality shifts requires new outcome-blind panels and
renewed measurement under their own starting policies.

Robotics studies share Anarres's identity, measurement, and evaluation
contracts while retaining domain-specific safety, simulator, and hardware
requirements.
