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

## Scored outcome

The primary prediction fails. At matched 3,500-example volume, the
finance-language treatment has 64.6% overt numerical hallucination, while the
financial-QA and numeracy treatment reaches 90.8%. The full-recipe prediction
also fails at all three reported detectability levels. The numeracy-enhanced
treatment raises hallucination from 82.5% to 90.8% at L1, from 34.6% to 45.8%
at L2, and from 3.8% to 13.3% at L3.

The abstention between the base and finance-language models avoids a false
preference, but the observed result is decisive: the base model has 5.4% L1
hallucination and a 4.7/5 summarization-quality score, compared with 82.5% and
1.6/5 after finance-language adaptation.

The failure identifies a missing coordinate. Content alignment with financial
numeracy does not imply alignment with a target that requires grounded
generation or abstention. The next representation must separate task-content
alignment from behavioral-contract and grounding-discipline alignment.
