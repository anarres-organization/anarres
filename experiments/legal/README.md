# Predictable environment selection for legal reasoning

Legal reasoning environments differ in doctrine, interaction depth, reward
structure, and the kinds of corrections a model must absorb. A mixture that is
useful for one starting policy may waste compute or weaken another capability.

This program asks:

> Can measurements collected from a starting policy guide the allocation of a
> fixed training budget across legal task generators?

The first release is a [prospective SylloGym panel](environment-selection/README.md).
It compares three mixtures over the same fourteen procedural task generators,
with the starting weights, trainer, reward code, update count, training seeds,
and evaluation panel held fixed.

A second record studies [LAB learning dynamics and regression
risk](lab-learning-dynamics/README.md) across 15 checkpoints, 180 tasks, and 34
practice areas. It asks whether outcome-blind workflow structure flags later
regressions when the complete target practice area is held out from fitting.

The frozen policy-response mixture had the highest observed mean, but its
advantage over the two controls was less than half a percentage point and the
training-seed intervals crossed zero. The evidence therefore supports
abstention, not a superiority claim.

## Scope

SylloGym tests multi-turn doctrinal reasoning with deterministic Python
verifiers. It is valuable because facts arrive progressively and may require a
model to revise an earlier conclusion. Its scope excludes document review,
citation provenance, tool use, artifact production, evolving matters, and
professional review.

Results remain specific to the pinned starting policy, task generators,
training contract, and evaluation endpoint. The LAB record contains one
continuing-RL intervention, so its task-level predictions are associations, not
causal task effects. A new legal workflow requires a new outcome-blind panel
and its own guardrails.
