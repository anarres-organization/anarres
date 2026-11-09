# Excluded-source numerical-faithfulness test

This record freezes task-level predictions for an external study titled
*When Financial Fine-tuning Fails: A Three-Level Detectability Analysis of
Numerical Hallucination in Domain-Adapted Language Models*. The study did not
enter the finance bridge, the strict task-level audit, or the revision of the
target-conditional representation.

The freeze uses only the reported intervention contract: an untouched base
model, a finance-language treatment, a broader treatment that adds financial
question answering and numeracy data, and a volume-matched comparison. Exact
outcome tables were not inspected before this record was committed.

## Frozen prediction

For numerical-faithfulness outcomes, the shared representation gives no
automatic credit to finance-language adaptation. It predicts:

1. the treatment containing explicit financial QA and numeracy supervision
   should outperform finance-language adaptation at matched volume
2. the same treatment should outperform finance-language adaptation when the
   complete reported recipes are compared
3. the base model and finance-language treatment remain an abstention because
   domain-language alignment alone does not establish numerical retention.

The first comparison is the primary test because it holds reported volume
constant. Target-level outcomes will be transcribed only after the freeze is
committed and the official source is verified.
