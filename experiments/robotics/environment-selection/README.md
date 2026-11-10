# Robot-data environment selection

This release studies whether pre-training evidence can guide a finite-budget
choice between robot-learning datasets.

## Evidence at a glance

| Record | Design | Main result | Appropriate conclusion |
| --- | --- | --- | --- |
| [Prospective PushT panel](prospective-pusht/README.md) | Three equal-episode subsets, three training seeds, fixed closed-loop evaluation | The frozen abstention set contained the observed best arm | The uncertainty-aware decision was safe in this panel |
| [Retrospective cross-source analysis](retrospective-bridge/README.md) | 31 retrospective panels, 111 candidate arms, eight task contexts | Practical rule: 65.4% pair ordering and 0.272 normalized regret | Interpretable measurements are promising. The fitted model is not yet incrementally useful. |
| [External checks](external-checks/README.md) | GUILD real-robot transport, SOLE-R1 reward-model falsification, and GreenBall initiation probe | Policy-responsive collection transfers, trajectory correlation alone fails, and initiation risk is measurable offline | Positive, negative, and mechanism-specific evidence must be reported together |
| [Prospective closed-loop curation v1.4.1](prospective-cupid-can-v141/README.md) | Corrected RoboMimic Can protocol with an early closed-loop qualification gate | The scoring policy passed with 95 successes and 5 failures across 100 episodes | Influence measurement may proceed, while candidate-policy outcomes remain unopened |
| [Prospective Square regression study](prospective-square-regression-v1/README.md) | Frozen 128-state panel, three probe policies, and five unopened half-data candidates | Measurement protocol and paired regression endpoint are frozen; candidate outcomes remain unopened | Probe-policy failures may guide candidate construction only after the qualification gate passes |
| [Invalidated v1.5 execution](prospective-cupid-can/README.md) | Earlier RoboMimic Can protocol execution | A provenance audit found a v1.5 dataset/runtime mismatch before candidate training | The execution cannot support a scientific conclusion about the intended v1.4.1 protocol |

## Decision workflow

```text
pin source and policy
    -> define a held-out target
    -> construct candidates without outcomes
    -> measure relevance, diversity, quality, reliability, and cost
    -> freeze a choice or abstention set
    -> train with matched budgets
    -> evaluate on the fixed target
    -> report regret, uncertainty, guardrails, and cost
```

The workflow deliberately keeps a competent practical baseline. A learned
model is useful only if it improves held-out decisions beyond that baseline and
survives negative controls.

## Why there are two records

Retrospective public studies provide breadth but can be affected by publication
choices and incomplete release artifacts. A prospective panel gives stronger
chronology but only narrow support. Reporting both prevents breadth from being
mistaken for causal validation and prevents one controlled experiment from
being mistaken for broad generality.

## Reproduce the prospective score

The prospective record uses only the Python standard library:

```bash
cd experiments/robotics/environment-selection/prospective-pusht
python scripts/reproduce.py
python -m unittest test_reproduce.py
```

The script recomputes arm means, allocation regret, paired seed contrasts,
confidence intervals, and whether the frozen abstention set retained the
observed best arm.

## Scientific boundaries

- Evaluation episodes are repeated measurements, not independent training
  interventions. Training seed is the independent unit in the prospective
  panel.
- Infrastructure failures must remain missing rather than becoming reward zero.
- A retrospective fit is not a prospective forecast.
- A correct abstention is not selector superiority.
- Results outside the measured policy, task, embodiment, and budget require a
  new validation panel.
