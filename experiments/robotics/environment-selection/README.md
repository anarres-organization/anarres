# Robot-data environment selection

This release studies whether pre-training evidence can guide a finite-budget
choice between robot-learning datasets.

## Evidence at a glance

| Record | Design | Main result | Appropriate conclusion |
| --- | --- | --- | --- |
| [Prospective PushT panel](prospective-pusht/README.md) | Three equal-episode subsets, three training seeds, fixed closed-loop evaluation | The frozen abstention set contained the observed best arm | The uncertainty-aware decision was safe in this panel |
| [Three-source bridge](retrospective-bridge/README.md) | 31 retrospective panels, 111 candidate arms, eight task contexts | Practical rule: 65.4% pair ordering and 0.272 normalized regret | Interpretable measurements are promising; the fitted model is not yet incrementally useful |
| [External checks](external-checks/README.md) | GUILD real-robot temporal check and SOLE-R1 outcome-blind public shadow test | Policy-responsive collection transfers; trajectory correlation alone fails | Positive and negative transport evidence must be reported together |

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
