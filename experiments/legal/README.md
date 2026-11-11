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
| Qualify a frontier legal workflow | [LAB workflow intake](lab-workflow-intake/README.md) | A model-agnostic intake validates practice areas, matter documents, deliverables, and criterion-level review structure before model responses or outcomes are read. |
| Pin a LAB runtime | [LAB execution contract](lab-workflow-intake/EXECUTION_CONTRACT.md) | A versioned record binds the starting policy, agent harness, judge harness, outcome semantics, accounting, and protected outcomes without starting execution. |

## Start here

```bash
uv tool install ./packages/legal
anarres legal status --repository .
anarres legal regressions --repository .
```

The status command shows which legal workflows are available. The regression
command reproduces the LAB task-risk result.

The SylloGym panel compares three mixtures over the same fourteen procedural
task generators with matched starting weights, trainer, reward code, updates,
seeds, and evaluation. The selected mixture had the highest observed mean, but
its advantage was below half a point and the seed intervals crossed zero. The
rule therefore abstained rather than claiming a resolved choice.

The LAB record covers 15 checkpoints, 180 tasks, and 34 practice areas. It
tests whether task and workflow structure available before continued training
can flag later regressions when the complete target practice area is excluded
from model fitting.

The LAB workflow intake adds the operational entry point for a new long-horizon
legal study. It validates a pinned LAB checkout without reading model responses
or downstream training outcomes. An **execution contract** is a versioned
specification of the model, agent harness, judges, accounting, validity rules,
and protected outcomes. Policy probing remains unavailable until that runtime
can execute the starting policy.

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
