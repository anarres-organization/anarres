# Frozen target-conditional holdout: Japanese financial documents

This audit tests the target-conditional representation on an independently
reported staged adaptation study for Japanese financial documents. The study is
absent from the fitted bridge and from the SNFinLLM and FEVO development audits.

The freeze uses only the public method description: a base checkpoint, a
financial text-adaptation stage, a subsequent visual financial-document stage,
and an ablation that removes an earlier prerequisite stage. It records three
predictions before result-table extraction:

1. financial text adaptation improves the text-finance target family over the
   unadapted checkpoint
2. visual financial adaptation improves the visual-document target family over
   the text-only checkpoint
3. the full staged path improves the combined financial-document target over the
   skip-stage ablation.

The representation abstains on general capabilities because the public method
description does not establish a retention comparison. Exact candidate names,
target names, and every comparable regression will be recovered after this
freeze. The audit remains a retrospective source-level holdout because the paper
was already public.

## Result

The first prediction is correct in aggregate, but its five task-level outcomes
include two regressions. Financial text adaptation improves three JP Fin Harness
subtasks and reduces two. The visual-stage prediction is unscorable because the
paper reports only text-input evaluations, leaving the page-image capability
without a matching outcome.

The full staged path does not uniformly outperform the skip-stage ablation. It
improves EDINET fraud detection and trails on EDINET industry classification and
JP Fin Harness. The paper treats EDINET earnings as near chance, so that row is
preserved but excluded from directional scoring. Across the eight meaningful
task-level comparisons covered by the frozen claims, four directions are
correct.

This holdout sharpens the representation again. Target conditioning must operate
at task level, and it must represent interference from later stages alongside
alignment. Broad target families can contain opposing treatment effects. The
unscored visual claim also shows that source admission should require an outcome
that directly exercises the capability targeted by the intervention.

[`OUTCOMES.json`](OUTCOMES.json) records the exact values and source audit.
[`SCORE.json`](SCORE.json) records the frozen comparison score.

## Reproduce

```bash
python score_holdout.py
python -m unittest test_score.py
```
