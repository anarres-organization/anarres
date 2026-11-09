# Capability-contract finance transfer representation

The strict task-level audit shows that a shared representation can transfer
across models when every candidate is defined relative to its evaluation task.
The excluded numerical-faithfulness source then reveals a remaining gap.
Financial numeracy data improves constrained calculation while sharply
increasing unsupported numerical generation during summarization. Content
alignment and behavioral alignment therefore require separate measurements.

Version 4 represents each candidate--target decision through six concepts:

- **content alignment:** overlap between training content and the knowledge or
  domain required by the target
- **supervision alignment:** overlap between demonstrated behavior and the
  capability scored by the target
- **verification alignment:** whether training feedback directly checks the
  target behavior
- **behavioral-contract alignment:** whether training and evaluation require
  compatible actions, including generation, extraction, abstention, tool use,
  evidence citation, or recommendation
- **prerequisite and retention coverage:** whether later training preserves the
  capabilities and constraints needed by the target
- **exposure and reliability:** effective training volume, candidate coverage,
  measurement reliability, and missingness.

For grounded-generation targets, behavioral-contract alignment includes three
measurements that remain distinct:

1. whether the training response must be supported by supplied evidence
2. whether unsupported output is penalized or abstention is rewarded
3. whether the target requires free generation, constrained calculation, or
   evidence-preserving extraction.

The numerical-faithfulness holdout and E2A-Bench provide independent evidence
for this separation. The holdout finds that numeracy supervision improves
calculation but weakens numerical restraint during summarization. E2A-Bench
finds that financial fine-tuning amplifies action imbalance across strict
base--fine-tuned pairs and that verification can improve support while reducing
coverage. Both results show that a training intervention can improve one
capability while changing the output policy in ways that reduce target utility.

The next excluded-source test must encode these six concepts before inspecting
target-level outcomes. It should report candidate ordering, normalized regret,
and abstention separately. Version 4 remains a research specification until it
passes that test and does not replace the frozen results produced by earlier
representations.

## Development evidence

- Li and Liu, *When Financial Fine-tuning Fails*,
  [arXiv:2609.04806](https://arxiv.org/abs/2609.04806)
- Wang, Xu, and Wang, *E2A-Bench*,
  [Findings of EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.450/)
