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
