# FinLCR component-ablation result

The prediction freeze was pushed in commit `ad0356d` before the paper PDF or
component outcomes were opened. The abstract-level claim visible before that
commit remains excluded from scoring.

Table 2 reports three matched comparisons needed by the frozen component
predictions. Adding staged context training to difficulty-aware sampling raises
the overall average by 4.37 points. Adding difficulty-aware sampling to staged
training raises it by 3.18 points. The combined recipe also raises the
long-context average by 3.91 points relative to difficulty-aware sampling
without staged context. All three directions match the freeze.

The combined recipe improves the short-context average by 1.37 points over
naive GSPO, matching the retention prediction. The paper does not provide a
matched component ablation for its highest-difficulty subset, so that prediction
remains unscored.

The interaction is scientifically important. Staged training alone lowers the
overall average by 0.85 points relative to naive GSPO, and difficulty-aware
sampling alone lowers it by 2.04 points. Their combination improves it by 2.33
points. This source therefore supports the joint representation while warning
against interpreting its environment coordinates as independently additive.
