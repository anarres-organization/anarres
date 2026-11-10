# Finance domain priorities

This audit asks which finance tasks provide a consequential, measurable, and
reproducible test of environment selection. It separates evidence about real
operational demand from the availability of public construction sources.

## Primary target: reconciliation and exception handling

The strongest initial target is high-precision reconciliation and controlled
exception handling across post-trade, collateral, payment, and ledger systems.
These workflows combine five properties needed for an environment-selection
study:

1. records can be generated with known correspondence and planted breaks
2. false matches and missed exceptions have different operational costs
3. tools change state under explicit approval and escalation rules
4. intermediate evidence can be checked independently of the final answer
5. difficulty can vary through ambiguity, missing data, timing, currency,
   lifecycle state, and cross-system disagreement.

This priority follows public operational evidence. The Bank of England and FCA
report that agent deployment is concentrated in decision support and constrained
execution, with Operations and IT the most common area for greater autonomy.
DTCC identifies automation in allocation, confirmation, and trade matching as
important to accelerated settlement. ISDA treats portfolio reconciliation,
data integrity, discrepancy investigation, and dispute escalation as core
collateral controls. BIS experiments further show that payment operations
require explicit trade-offs between liquidity, priority, and settlement delay.

Primary references:

- [Bank of England and FCA 2026 AI survey](https://www.bankofengland.co.uk/report/2026/artificial-intelligence-in-uk-financial-services-2026)
- [DTCC accelerated-settlement resources](https://www.dtcc.com/initiatives/accelerated-settlement/faqs-and-resources)
- [ISDA collateral-management practices](https://www.isda.org/collateral-management-sop/)
- [BIS AI agents for cash management](https://www.bis.org/publications/working-paper-1310-ai-agents-cash-management-payment-systems)

## Convergence in current finance-agent systems

Recent product and benchmark releases reinforce the same task choice from
different directions. Anthropic's finance-agent templates include general-ledger
reconciliation, month-end close, statement audit, KYC screening, and valuation
review. Ramp describes reconciliation, journal entries, variance analysis,
accruals, expense controls, procurement review, and close workflows. OpenAI's
Endex case study emphasizes model reconciliation, discrepancy detection, and
source-linked review of financial documents. Stripe's finance automation work
describes accounting, treasury, tax, payments, reporting, reconciliation, and
the validation and monitoring needed to operate agents in those workflows.

Primary references:

- [Anthropic finance-agent templates](https://www.anthropic.com/news/finance-agents)
- [Ramp agents for finance teams](https://ramp.com/blog/ramp-agents-announcement)
- [Ramp Stack accounting workflows](https://ramp.com/stack)
- [OpenAI and Endex financial analysis](https://openai.com/index/endex/)
- [Stripe finance-agent responsibilities](https://stripe.com/careers/listing/ai-solutions-program-manager-finance/8221776)

The public research frontier now includes complementary evaluation resources.
FORCE-Bench covers ERP obligation research, time-bounded entity research, and
multi-source business briefs under latency constraints. FinBalance evaluates
document-grounded journal entries, final balance sheets, citations, and
contradiction handling with deterministic ledger replay. Business Bench covers
stateful bookkeeping and finance operations. These resources support a focus
on evidence-grounded accounting work rather than a generic finance chatbot.

- [FORCE-Bench](https://arxiv.org/abs/2607.19409v1)
- [FinBalance](https://arxiv.org/abs/2606.15949v1)
- [Business Bench](https://businessbench.org/paper)

## Construction-source decision

No single open source currently satisfies the full post-trade construction
contract.

[FINOS Common Domain Model](https://github.com/finos/common-domain-model)
provides the strongest public representation of trades and lifecycle events.
It can anchor deterministic trade states and event semantics, but it is not an
agent benchmark or discrepancy generator by itself.

[RecBench](https://huggingface.co/datasets/end-close/recbench) provides a
large synthetic three-way reconciliation dataset with exact correspondence and
exception labels. Its public dataset card describes a generator and evaluator,
but the pinned repository snapshot does not contain that code. RecBench is
therefore an external design and evaluation source until the missing generator
can be recovered and audited.

[Business Bench](https://github.com/erphq/business-bench) is the first
generator-qualified source in this program. Its close, accrual, and payment
workflows support a prospective experiment now, while a post-trade generator is
built from independently audited lifecycle and reconciliation components.

[FinBalance](https://arxiv.org/abs/2606.15949v1) is a particularly close
external design reference because its deterministic ledger separates reported
balance-sheet accuracy from the balance sheet implied by a model's journal
entries. Its ablations show that ledger feedback can repair aggregation while
weakening contradiction detection. This supports keeping task completion,
evidence binding, ledger consistency, and inconsistency handling as separate
outcomes. The paper reports a generator, but a reusable public repository has
not yet been pinned in this program, so it is not a construction source.

## Evaluation contract

A post-trade study should report more than aggregate completion. The minimum
outcome vector is:

- match precision at a prespecified operating point
- exception recall by discrepancy type and difficulty
- false-match cost and missed-break cost
- root-cause classification and evidence provenance
- correct escalation, approval, and abstention behavior
- state consistency after every tool action
- generated tokens, tool calls, wall time, and measurement cost.

The primary allocation decision should be made at a precision floor rather than
by unconstrained accuracy. This reflects the asymmetric cost of silently
accepting an incorrect reconciliation.

## Other finance tracks

Investment research and artifact production remain important external tracks.
BankerToolBench, FrontierFinance, and the SecondState Finance Agent Benchmark
provide useful tests of document synthesis, multi-file reasoning, and tool use.
Quantitative strategy coding and liquidity management require separate risk and
execution contracts. Results from one track should not be pooled with another
until their outcomes and control requirements are explicitly aligned.
