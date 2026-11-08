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

The first study focuses on accounting and finance operations. This setting
supports generated scenarios with planted truth, executable checks, stateful
tools, and explicit authorization rules. It also creates a real allocation
decision between candidate training mixtures rather than a retrospective
comparison of benchmark scores.

## Research path

The [environment-selection study](environment-selection/README.md) begins with
source qualification. Four stateful Business Bench workflows passed strict
reference, null-agent, negative-control, handbook, and state-determinism checks
across five generated seeds each. This establishes that the generators can
support a prospective panel. It provides no evidence yet about which training
mixture is best.

The planned experiment will:

1. generate disjoint development, candidate, and held-out scenario partitions
2. measure each candidate under one frozen starting policy and tool contract
3. construct policy-relative and practical baseline mixtures without reading
   trained-policy outcomes
4. freeze candidate identities, predictions, budgets, and material-control
   guardrails
5. train every arm under the same optimization contract
6. open the held-out outcomes only after completeness and identity checks pass.

The primary outcome is held-out executable task completion. Allocation regret
measures the cost of choosing a candidate other than the observed best arm.
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

The first panel covers generated accounting workflows under one agent harness,
starting policy, and training contract. It will not establish a universal
finance-task selector. Investment research, underwriting, market analysis,
spreadsheet modeling, and money movement require separate candidate panels and
evaluation contracts. Actions with financial authority remain approval-gated.
