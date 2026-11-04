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

The frozen policy-response mixture had the highest observed mean, but its
advantage over the two controls was less than half a percentage point and the
training-seed intervals crossed zero. The evidence therefore supports
abstention, not a superiority claim.

## Scope

SylloGym tests multi-turn doctrinal reasoning with deterministic Python
verifiers. It is valuable because facts arrive progressively and may require a
model to revise an earlier conclusion. It is not a complete legal workflow: it
does not test document review, citation provenance, tool use, artifact
production, evolving matters, or professional review.

Results remain specific to the pinned starting policy, task generators,
training contract, and evaluation endpoint. A new legal workflow requires a
new outcome-blind panel and its own guardrails.
