# Post-trade source audit

This audit records whether public sources can support a prospective post-trade
environment-selection experiment. It evaluates construction support rather than
benchmark prominence.

## FINOS Common Domain Model

- Repository: <https://github.com/finos/common-domain-model>
- Pinned commit: `3865246388d045f96dfa7a8ce1c0672efe6fa8cf`
- Repository version: `8.0.0-dev.14`
- Specification license: Community Specification License 1.0
- Relevant content: typed products, trade states, lifecycle events, settlement,
  collateral, securities lending, and FpML translation examples.

The model provides authoritative lifecycle semantics and executable data
structures. It does not provide an agent task harness, planted discrepancy
generator, or outcome protocol. It is admitted as a representation candidate,
not as a qualified prospective construction source.

## RecBench

- Dataset: <https://huggingface.co/datasets/end-close/recbench>
- Pinned commit: `8cf65de21434a480cb3a499e3c39246c9e8b744a`
- Dataset license: CC BY 4.0
- Relevant content: synthetic ledger, processor, payout, and bank-statement
  records with exact reconciliation and exception labels.

The dataset card describes generator, evaluation, documentation, and test
directories. The pinned repository tree contains the dataset card, release
metadata, and generated datasets, but not the described generator or evaluator.
The released data can support an external reconciliation check. It cannot yet
support outcome-blind candidate construction or independent scenario generation.

## Decision

The immediate prospective experiment remains on the qualified Business Bench
workflows. A post-trade panel should combine an audited lifecycle representation
with a separately tested discrepancy generator and a precision-first evaluator.
Construction begins only after deterministic oracle, null-agent, negative-control,
state-integrity, and licensing gates pass.

## Additional design references

[TradeOpsSim AgentEnv](https://huggingface.co/datasets/AlexSchwartzman/TradeOpsSim-AgentEnv)
is pinned at `c1c6f00303590f146a20bec690b5b648d19e3824`. It releases executable
bundles, tests, trajectories, and thirteen synthetic trade-reconciliation
fixtures under Apache-2.0. The source explicitly describes these fixtures as a
demonstration rather than a held-out benchmark, and its transparent rules policy
passes all thirteen. It is useful for harness and evidence-contract design, but
its current task bank is too small and too solved for the claim-bearing panel.

[FinRCA-Bench](https://arxiv.org/abs/2608.18534) reports 2,250 deterministic
accounts-payable-to-bank reconciliation cases across 14 tables and 15 injected
failure types. Its separation of evidence retrieval, root-cause accuracy, and
returned-evidence contracts is directly relevant to the evaluation design. A
reusable benchmark repository was not identified during this audit, so the paper
is retained as a design reference rather than a construction source.
