# Mint-Agent excluded-source transfer

This audit applies the pre-existing capability-contract representation to a
released frontier agentic-finance integration decision. Mint-Agent develops
separate reasoning and execution specialists, then compares static TIES merging
with multi-teacher on-policy distillation (MOPD) at 9B.

The representation predicts that task-routed on-policy supervision should
preserve the two capability contracts more reliably than static parameter
merging. The comparison is evaluated separately on FinanceBench, BizFinBench,
FinanceAgentBench v1.1, and FinSearchComp T2.

## Result

MOPD outperforms TIES on all four benchmarks, by 1.33, 3.86, 4.00, and 3.19
points. The representation therefore gets 4/4 directions correct with zero
pairwise regret. These outcomes remain one source-level test because they arise
from one controlled integration experiment.

This is a retrospective excluded-source test. The source was public before
scoring and did not enter representation design or fitting.

## Reproduce

```bash
python score_holdout.py
python test_score.py
```

The audit uses [Mint-Agent v2](https://arxiv.org/abs/2608.16386v2).
