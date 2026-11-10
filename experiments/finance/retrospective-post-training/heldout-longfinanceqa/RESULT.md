# LongFinanceQA outcome-separated result

The frozen representation is supported on all four prediction families for
which the paper reports a matched control. Across 25 table-level comparisons,
24 have the predicted direction. Supervised intermediate reasoning improves
the overall financial long-context score in all four context bands and improves
11 of 12 multi-source task-band comparisons. It also retains or improves the
single-source score in all four bands. Full PAI outperforms its variant without
property extraction in every reported context band and in the aggregate.

The only directional miss is clustering at 10K--50K tokens, where answer-only
supervision scores 6.50 points higher. The paper does not separately ablate
property-based retrieval or intermediate summarization, so those frozen
predictions remain unscored.

This is one outcome-separated source-level test. The 25 comparisons describe
its internal coverage and are not treated as independent studies. The overall
gains disclosed in the abstract remain excluded from the score.

## Reproduce

```bash
python score_holdout.py
python test_score.py
```

Source: [Lin et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.615/).
