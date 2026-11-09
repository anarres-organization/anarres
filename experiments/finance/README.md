# Predictable environment selection for agentic finance

Financial agents must do more than retrieve a fact or produce a plausible
answer. They reconcile records, preserve controls, create reviewable work
products, and act through tools whose mistakes can change financial state. A
training distribution can improve task completion while weakening a ledger
tie, approval rule, or evidence trail.

This program asks:

> Can measurements from a starting policy help choose a finance-task
> distribution that improves held-out work at a fixed training budget while
> preserving material controls?

**Start here:** the [finance research brief](RESEARCH_BRIEF.md) summarizes the
completed evidence, the qualified accounting experiment, and the prospective
post-trade extension in one page.

The operational studies focus on control-heavy finance work. Reconciliation,
settlement exceptions, collateral disputes, payment controls, and close
workflows have planted truth, executable checks, stateful tools, and explicit
authorization rules. They also create real allocation decisions between
candidate training mixtures rather than retrospective comparisons of benchmark
scores.

## Research path

The [domain-priority audit](DOMAIN_PRIORITIES.md) identifies reconciliation and
exception handling as the primary operational target. The
[environment-selection study](environment-selection/README.md) begins with
source qualification. Four stateful Business Bench workflows passed strict
reference, null-agent, negative-control, handbook, and state-determinism checks
across five generated seeds each. This establishes that the generators can
support a prospective panel. It provides no evidence yet about which training
mixture is best.

Any prospective training experiment will:

1. generate disjoint development, candidate, and held-out scenario partitions
2. measure each candidate under one frozen starting policy and tool contract
3. construct policy-relative and practical baseline mixtures without reading
   trained-policy outcomes
4. freeze candidate identities, predictions, budgets, and material-control
   guardrails
5. train every arm under the same optimization contract
6. open the held-out outcomes only after completeness and identity checks pass.

The [retrospective post-training audit](retrospective-post-training/README.md)
separately normalizes published finance interventions. It asks which recurring
properties of training data and reward design predict improvement across prior
studies. Two frozen source-level holdouts then test transfer to excluded model
families, languages, pipelines, and targets. They support target-aligned domain
adaptation while showing that later-stage effects require task-level alignment,
interference, and retention measurements.

The [agent-systems evidence map](agent-systems-evidence/README.md) audits the
workflow side of the decision. It separates post-training interventions from
tool and scaffold ablations, and identifies reconciliation, spreadsheet work,
evidence-grounded research, and workflow orchestration as the strongest public
task families.

The primary prospective outcome is held-out executable task completion.
Allocation regret measures the cost of choosing a candidate other than the
observed best arm.
Ledger integrity, authorization violations, evidence provenance, and
unauthorized state changes remain separate guardrails. A high aggregate score
cannot erase a material-control failure.

## Relationship to frontier finance agents

Current systems span research, spreadsheet modeling, accounting operations,
document review, and controlled tool use. [OpenAI's financial-services
workspace](https://openai.com/index/introducing-chatgpt-financial-services/)
and [ChatGPT for Excel](https://openai.com/index/chatgpt-for-excel/) emphasize
research, modeling, and artifact production. [Anthropic's finance
agents](https://www.anthropic.com/news/finance-agents) emphasize connected data,
tool permissions, managed credentials, and audit logs. [Ramp Accounting
Bench](https://labs.ramp.com/accountingbench) evaluates accounting work inside
synthetic business worlds, while [Stripe's finance-agent
guide](https://stripe.com/guides/a-founders-guide-to-delegating-finance-work-to-agents)
describes document processing, reconciliation, review, and staged authority.

These systems motivate the task class and its guardrails. They do not provide
the outcome data for this study. The study uses openly qualified generators and
keeps research, accounting operations, and authority-bearing actions as
distinct endpoints.

## Scope

The generator-qualified panel covers accounting workflows under one agent
harness, starting policy, and training contract. A post-trade panel will require
its own lifecycle model, discrepancy generator, and precision-first evaluation.
Neither panel can establish a universal finance-task selector. Investment
research, underwriting, market analysis, spreadsheet modeling, and money
movement require separate candidate panels and evaluation contracts. Actions
with financial authority remain approval-gated.

## Public artifacts

- [Research brief](RESEARCH_BRIEF.md)
- [Finance domain-priority audit](DOMAIN_PRIORITIES.md)
- [Prospective environment-selection protocol](environment-selection/README.md)
- [Starting-policy qualification](environment-selection/STARTING_POLICY_QUALIFICATION.md)
- [Post-trade source audit](environment-selection/POST_TRADE_SOURCE_AUDIT.md)
- [Post-trade panel specification](environment-selection/POST_TRADE_PANEL_SPEC.md)
- [Retrospective post-training audit](retrospective-post-training/README.md)
- [Frozen SNFinLLM source holdout](retrospective-post-training/heldout-snfinllm/README.md)
- [Frozen Japanese financial-document holdout](retrospective-post-training/heldout-japanese-multimodal/README.md)
- [Expanded machine-readable results](retrospective-post-training/results/expanded_summary.json)
- [Agent-systems evidence map](agent-systems-evidence/README.md)
