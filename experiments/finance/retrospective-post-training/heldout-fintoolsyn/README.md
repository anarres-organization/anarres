# FinToolSyn excluded-source transfer

This audit applies the pre-existing capability-contract representation to a
released agentic-finance study that did not enter representation design or
fitting. FinToolSyn holds Qwen3-8B, function-calling mode, LoRA settings, and
training duration fixed while varying how financial tool-use dialogues are
constructed.

The representation predicts that forward synthesis should preserve
clarification and rejection behavior better than reverse tool-conditioned
synthesis. It also predicts that dynamic retrieval noise should improve the
balanced environment and tool-call target over a clean static candidate set.

## Result

All nine high-confidence directional comparisons are correct. The predicted
best candidate is correct for both the balanced average and tool-call targets,
and all three prespecified improvement or regression directions are correct.
Reverse synthesis improves tool calling by 15.96 points over the base while
reducing the non-tool score by 37.74 points and the balanced average by 10.89
points. Full FinToolSyn ranks first on the balanced and tool-call targets.

The representation abstains from ordering the base, static, and full variants
on the non-tool score because starting-policy retention and target-aligned
supervision point in different directions. The paper's appendix also reports a
separate non-tool accuracy aggregation whose ordering differs from the primary
non-tool score. Both are retained without collapsing them into one target.

This is one retrospective excluded-source test. Its evidence comes from the
controlled agentic setting and the correctly identified regression.

## Reproduce

```bash
python score_holdout.py
python test_score.py
```

The audit uses the [peer-reviewed ACL Anthology record](https://aclanthology.org/2026.findings-acl.746/).
