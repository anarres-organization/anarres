# Predictable environment selection for finance agents

Finance agents must reconcile records, preserve controls, produce reviewable
work, and use tools whose mistakes can change financial state. A training
environment may improve task completion while weakening a ledger tie,
authorization rule, or evidence trail.

This program asks whether measurements from a starting policy can help choose
a finance-task distribution that improves held-out work at a fixed budget while
preserving material controls.

## Start here

Install the native CLI and finance adapter from a repository checkout:

```bash
cargo install --path crates/anarres-cli --locked
uv tool install ./packages/finance
anarres adapter doctor finance
anarres finance status
```

Reproduce the released evidence with:

```bash
anarres finance verify
anarres finance reproduce --output-dir .anarres/finance-reproduction
```

Use `--repository /path/to/anarres` when running the evidence commands outside
the checkout. The [finance research brief](RESEARCH_BRIEF.md) gives a compact
summary of the completed evidence and next prospective test.

## Evidence at a glance

| Test | Result |
| --- | --- |
| Task-level candidate ordering | 81.6% across 79 panels without model identity |
| Source-held-out confidence filter | 90.4% over 235 decided pairs at 76.1% coverage |
| Regression-risk audit | 0.815 source-macro ROC AUC, compared with 0.575 for data volume |
| FinToolSyn controlled ablation | 9/9 high-confidence directions and 3/3 improvement or regression calls |
| LongFinanceQA component test | 24/25 matched comparisons follow the predicted direction |
| Finance-data continual-pretraining holdout | 21/22 candidate-target directions across two backbones |

The compact representation describes the capabilities an intervention trains
and the controls its target requires. It transfers across several retrospective
studies, but it is not yet a prospectively validated universal selector.

## Prospective workflow

Four stateful accounting workflows passed reference, no-op, negative-control,
handbook, and state-determinism checks across five generated seeds. This
qualifies the generators for a prospective panel. It does not identify the best
training mixture.

The next matched experiment will:

1. generate disjoint development, candidate, and held-out scenarios
2. measure candidates under one frozen starting policy and tool contract
3. freeze candidate identities, predictions, budgets, and control guardrails
4. train every arm under the same optimization contract
5. open held-out outcomes only after completeness and identity checks pass.

The primary outcome is executable task completion. Ledger integrity,
authorization violations, evidence provenance, and unauthorized state changes
remain separate guardrails. A high aggregate score cannot erase a
material-control failure.

The adapter also accepts a complete
[`anarres.finance-candidate-panel.v1`](../../schemas/finance-candidate-panel.v1.schema.json)
record:

```bash
anarres finance decide candidate-panel.json
```

The released rule selects a candidate only when its margin clears the frozen
threshold; otherwise it reports the unresolved set. This rule is
retrospectively calibrated and still requires prospective validation.

## Research structure

- [`environment-selection/`](environment-selection/) contains the source
  qualification and prospective accounting protocol.
- [`retrospective-post-training/`](retrospective-post-training/) normalizes
  published interventions and runs source-held-out transfer tests.
- [`agent-systems-evidence/`](agent-systems-evidence/) maps public evidence for
  reconciliation, spreadsheet work, grounded research, and orchestration.
- [`adaptive-environment-generation/`](adaptive-environment-generation/)
  specifies a repeated generate, screen, admit, and evaluate loop.
- [`DOMAIN_PRIORITIES.md`](DOMAIN_PRIORITIES.md) explains why reconciliation
  and exception handling are the first operational targets.

## Scope

The qualified generator panel covers accounting workflows under one agent
harness, starting policy, and training contract. Post-trade operations require
a separate lifecycle model and precision-first evaluation. Investment
research, underwriting, market analysis, spreadsheet modeling, and money
movement require their own candidate panels and outcome contracts. Actions with
financial authority remain approval-gated.

Known-correct records and outcomes make reconciliation and exception handling
useful experimental settings. They do not make the environments interchangeable
with other finance tasks, nor do they remove the need for review and access
controls.
