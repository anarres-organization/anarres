# Excluded-source test: financial tools and experience memory

This audit applies the pre-existing capability-contract representation to
FinAcumen, a financial multimodal reasoning system that was not used to design
or fit the representation. The source holds model weights fixed within each
panel and varies deterministic financial tools, conditional experience memory,
and the fields supplied by that memory.

The representation predicts that target-aligned tools should improve tasks that
require numerical execution, retrieval, visual decoding, and answer
verification. It further predicts that experience should add value when it
contains reusable strategies and failure-derived cautions, is retrieved by task
similarity, and falls back safely when no entry qualifies. These properties are
defined relative to the task contract rather than a model name.

## Result

The predicted ordering holds in every scored comparison. Across 16 nested
decision panels, the representation orders 33 of 33 non-tied candidate pairs
and selects an observed best candidate with zero normalized regret in every
panel. Four comparisons between Reflexion and ExpeL are intentionally
unranked because the representation does not distinguish their remaining
implementation differences.

The result includes several distinct checks:

- deterministic financial tools improve the frozen Qwen3-VL-8B backbone, and
  conditional structured memory improves it again
- the full memory contract ranks above experience without personalized
  directives, directives without experience, question-and-answer references,
  and question-only references
- the full system improves all six reported benchmark settings
- conditional structured memory leads Reflexion and ExpeL on four shared
  targets under the same backbone and tool environment
- the intervention direction transfers to GLM-4.6V, GPT-4o-mini,
  Gemini-2.5-Flash-Lite, and Qwen3-VL-235B-A22B.

This is one retrospective excluded-source test of a representation committed
before the source entered the analysis. Prospective validation remains future
work, and the nested rows share one study. The same task-conditional description
predicts controlled decisions across several targets and model families without
using model identity.

[`CONTRACT.json`](CONTRACT.json) records the chronology and predictions.
[`OUTCOMES.json`](OUTCOMES.json) records the source-native controlled rows.
[`SCORE.json`](SCORE.json) records the scored result.

## Reproduce

```bash
python score_holdout.py
python -m unittest test_score.py
```
