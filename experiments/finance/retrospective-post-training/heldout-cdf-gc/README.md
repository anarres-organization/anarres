# CDF-GC excluded-source transfer

This audit applies the pre-existing capability-contract representation to a
released finance data-selection study that did not enter representation design
or fitting. CDF-GC compares finance-domain continual pre-training candidates
under shared model-specific contracts on Llama-3.2-1B and Qwen2.5-0.5B.

The representation predicts that selection combining quality control with
complexity and diversity should lead the finance target. It separately predicts
that finance continual pre-training without an explicit retention mechanism can
reduce general capability relative to the starting model. Comparisons among the
remaining one-coordinate selection methods are left unresolved.

## Result

Twenty-one of 22 scored candidate-target directions are correct across the two
backbones. CDF-GC is correctly selected for both CFinBench panels. The starting
model is correctly selected for general retention on Qwen2.5-0.5B, while
CDF-GC exceeds it by 0.5 points on Llama-3.2-1B. The four panel-level choices
give 3/4 best-candidate accuracy and 0.096 mean normalized regret.

This result tests both improvement and regression risk under a model-agnostic
representation. The nested panels remain one retrospective excluded-source
test because the source was public before scoring.

## Reproduce

```bash
python score_holdout.py
python test_score.py
```

The audit uses the [peer-reviewed EMNLP 2025
record](https://aclanthology.org/2025.emnlp-main.1121/).
