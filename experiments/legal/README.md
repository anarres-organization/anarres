# Predictable environment selection for legal reasoning

Legal reasoning environments differ in doctrine, interaction depth, reward
structure, and the kinds of corrections a model must absorb. A mixture that is
useful for one starting policy may waste compute or weaken another capability.

This program asks:

> Can measurements collected from a starting policy guide the allocation of a
> fixed training budget across legal task generators?

## Results at a glance

| Decision | Public test | Result |
| --- | --- | --- |
| Select a training mixture | [Prospective SylloGym panel](environment-selection/README.md) | A frozen policy-response rule selected the observed best of three mixtures. Its advantage was too small and uncertain to justify replacing the controls, so the rule abstained. |
| Flag regression risk | [LAB learning dynamics](lab-learning-dynamics/README.md) | Task and workflow structure predicted later regressions in held-out practice areas with 0.648 ROC AUC and captured 37.0% of regressions in the highest-risk 20% of tasks. |

The SylloGym panel compares three mixtures over the same fourteen procedural
task generators. Starting weights, trainer, reward code, update count, training
seeds, and evaluation are matched. The frozen policy-response mixture achieved
the highest observed mean. Its advantage over the two controls was less than
half a percentage point, and the training-seed intervals crossed zero.
The release also includes a native adapter that projects the complete
outcome-blind pre-training measurement into compatible environment profiles.

The LAB record covers 15 checkpoints, 180 tasks, and 34 practice areas. It
tests whether task and workflow structure available before continued training
can flag later regressions when the complete target practice area is excluded
from model fitting.

Together, these studies exercise both sides of environment qualification:
ranking candidate training mixtures and identifying downstream regression
risk. The results support the workflow while preserving uncertainty when the
available evidence cannot justify a training decision.

## Scope

SylloGym tests multi-turn doctrinal reasoning with deterministic Python
verifiers. It is valuable because facts arrive progressively and may require a
model to revise an earlier conclusion. Its scope excludes document review,
citation provenance, tool use, artifact production, evolving matters, and
professional review.

Results remain specific to the pinned starting policy, task generators,
training protocol, and evaluation endpoint. The LAB record contains one
continuing-RL intervention, so its task-level predictions are associations, not
causal task effects. A new legal workflow requires a new outcome-blind panel
and its own guardrails.
