# Evidence map for agentic finance tasks

This map identifies finance workflows where environment selection can be tested
against a real operational decision. It is separate from the post-training
bridge because changes to tools and agent scaffolds are not training-data
interventions.

## Strongest task convergence

### Reconciliation, close, and audit

This is the strongest first task family. It appears in current product systems,
public benchmarks, and controlled ablations. The work has executable structure:
records must tie, journal entries must balance, evidence must support each
change, and unresolved cases must be escalated.

- [FinBalance](https://aclanthology.org/2026.findings-emnlp.675/) evaluates
  source-document reconciliation, cited journal entries, final balance sheets,
  and planted inconsistencies. Ledger feedback substantially improves reported
  balance sheets, while citation pressure alone barely changes document-linking
  errors.
- [Finch](https://aclanthology.org/2026.findings-acl.523/) contains 384 tasks
  inside 172 spreadsheet-centered enterprise workflows. The workflows combine
  retrieval, calculation, modeling, validation, and reporting over 1,710
  spreadsheets and supporting artifacts.
- [FinMaster](https://aclanthology.org/2026.findings-acl.385/) spans the full
  transaction-to-statement workflow across accounting, audit, analysis, and
  consulting.
- [FinancialAuditBench](https://arxiv.org/abs/2609.32835) provides 90 staff and
  review tasks across six synthetic engagements, including completed
  workpapers, supporting files, and procedure-specific grading.
- [Anthropic's finance-agent templates](https://www.anthropic.com/news/finance-agents)
  include ledger reconciliation, month-end close, statement audit, valuation
  review, KYC, and model maintenance.
- [OpenAI's Model ML case study](https://openai.com/index/model-ml/) emphasizes
  evidence reconciliation, source-linked calculations, editable financial
  models, and review-ready work products.

The prospective panel should therefore keep balance integrity, evidence
linkage, false matches, missed breaks, and authority violations as separate
outcomes. Aggregate task completion cannot erase a material-control failure.

### Financial research and model reconciliation

This is the strongest second task family. It matches work performed by banks,
investment firms, and advisory teams, but evaluation must separate factual
grounding from persuasive analysis.

- [Finance Agent Benchmark](https://arxiv.org/abs/2508.00828) contains 537
  expert-authored SEC research questions across nine task categories. Its best
  reported agent reaches 46.8% accuracy at an average cost of $3.79 per query.
- [AgenticFinBench](https://arxiv.org/abs/2611.04813) contains 230 real-world
  requests across eight categories and 18 model-harness configurations. Its
  claim audit lowers the rubric-only leader by 7.58 points, and harness choice
  explains more grounding variation than model choice in the complete
  comparison.
- [FinNextAssist](https://arxiv.org/abs/2610.03174) uses typed evidence,
  executable finance skills, and dedicated table and heterogeneous-evidence
  agents. Its 2x2 component ablation raises overall score from 42.7 to 48.5 and
  calculation from 55.0 to 75.0 when both specialist agents are present.
- [DealTrace](https://aclanthology.org/2026.finnlp-1.52/) decomposes deal
  analysis into extraction, reconciliation, forecasting, market context, and
  recommendation. Forecast repair is the only repair that improves every
  tested model, while an added critique pass raises cost without reliable gain.

These sources argue for candidate environments that vary evidence quality,
calculation burden, forecast structure, and source diversity rather than only
surface difficulty.

### Disclosure review and controlled improvement

Recent disclosure systems make the improvement contract explicit. They connect
feedback to one requirement, preserve protected cases, and evaluate the final
artifact rather than rewarding a plausible intermediate response.

- [FilingLoop](https://arxiv.org/abs/2610.37905) reconstructs 380 SEC disclosure
  reviews with 6,099 eligible requirements. Requirement-level procedural
  feedback raises fulfillment from 24.28% to 27.96% and full comment resolution
  from 16.90% to 20.75%, while harmful-revision prevalence falls from 5.8% to
  4.5% under the common audit.
- [FINSKILLOPS](https://arxiv.org/abs/2609.19680) turns typed SEC-filing QA
  failures into scoped skills with targeted validation, negative controls, and
  protected-case regression checks. Six of 33 proposed skills are promoted in
  its operational study, while monitoring non-correctness falls from 20.0% to
  12.5%.
- [FinReportBench](https://arxiv.org/abs/2608.04374) evaluates 244 bilingual
  report-generation tasks with a 35-item expert rubric. Benchmark-guided skill
  distillation improves institutional report properties across five model
  families while preserving basic deliverability.

These studies motivate candidate measurements for feedback scope, protected
coverage, grounding requirements, artifact-level verification, and the cost of
admission. They also show why a generic label such as financial fine-tuning is
too coarse for predicting a real workflow.

Financial safety adds a separate deployment contract.
[FinHarmBench](https://aclanthology.org/2026.acl-industry.117/) measures harmful
financial prompts, confusable benign requests, external finance capability, and
general capability before and after refusal steering distillation. Its matched
interventions show why a candidate should clear explicit harm and over-refusal
guardrails before capability gains inform allocation.

### Retained experience and procedural skills

Finance agents can also improve through reusable procedures, tools, and memory.
These interventions create environment decisions even when model weights remain
fixed.

- [FinSkillBench](https://arxiv.org/abs/2608.18099) evaluates 2,603 verifiable
  investment-management episodes across portfolio construction, risk
  management, and fundamental analysis. Curated procedural documents and tools
  raise the reported mean score from 0.366 to 0.528. Skills generated within the
  episode provide little benefit at higher cost, while a separate Hermes harness
  reproduces the direction across all three domains.
- [FinEvo-Bench](https://arxiv.org/abs/2608.06144) follows 120 professional
  finance tasks across 20 business scenes and six domains. Paired controls show
  gains of 9.33--19.37 points from retained experience across four agent
  scaffolds. Skill-only evolution gives the strongest Claude Code result, and
  rubric feedback outperforms reference-answer feedback across all four
  scaffolds.
- [Auditing Self-Evolution in Financial
  Agents](https://arxiv.org/abs/2608.17684) evaluates retained experience in a
  simulated e-banking system with sealed endpoints and state replay. Capability
  gains can coincide with greater exposure to injected content and more
  unauthorized state changes, so utility, exposure, and financial-state safety
  remain separate outcomes.
- [InKH](https://arxiv.org/abs/2606.01886) compares six memory and tool
  architectures over 24 seeds and four rounds. Write-time invalidation improves
  quality after simulated regime shocks without increasing retained knowledge,
  while also reducing stale-memory use. Its outcomes are architecture-level
  synthetic evidence rather than live financial performance.

These results support candidate environments that vary the carrier of
experience, the availability of executable procedures, feedback specificity,
and control coverage. They also suggest measurements of operation support,
recovery paths, retained-task coverage, and compliance burden before choosing
which experience to preserve. These public outcomes guide the candidate design
and do not qualify Anarres's prospective selector.

### Tool orchestration under operational constraints

Tool access alone is not a sufficient environment description.

- [RealFin](https://aclanthology.org/2026.findings-emnlp.341/) contains 1,524
  tasks from 108 workflow templates and 85 callable finance tools. It measures
  tool selection, ordering, parameter planning, temporal grounding, completion,
  and recovery.
- [FORCE-Bench](https://arxiv.org/abs/2607.19409) covers ERP obligation
  research, time-bounded entity research, and multi-source business briefs. It
  scores accuracy, citations, groundedness, recency, relevance, depth, clarity,
  and structure under latency constraints.
- [Do Tools Matter, or Just Their Descriptions?](https://aclanthology.org/2026.finnlp-1.54/)
  holds GPT-5 fixed across six tool surfaces. The full configuration beats the
  restricted baseline by 3.6 points, but a description-only control remains
  within one point while the nominal system tools run on fewer than 0.2% of
  samples.

The environment representation should therefore include tool dependency,
description quality, evidence availability, temporal requirements, and recovery
paths. Tool count is a poor standalone proxy.

## Measurement contract

The retrospective studies support a broader finance representation than any
single pair of rollout statistics. Candidate distributions should record:

- target and workflow alignment
- example count, source diversity, and real or synthetic composition
- evidence completeness, authority, provenance, and temporal validity
- calculation, reconciliation, forecasting, and tool-dependency structure
- explicit quality control, retention control, and verifier coverage
- policy-relative difficulty and failure variation
- response, tool, verifier, and measurement cost
- control burden, including approval, abstention, and escalation requirements.

Usable signal density and effective coverage remain candidate measurements
when RL is used. They sit inside this representation rather than defining the
finance project.

## Experimental consequence

The next tests use released studies as source-held-out decision panels. They ask
which procedure, tool, feedback type, memory contract, or scoped skill should
be promoted for later financial work. Candidate measurements and the selection
rule remain fixed while each excluded source is scored. Promotion, rejection,
regression, and abstention stay separate, as do capability, control, and cost
outcomes. The [adaptive environment-generation
protocol](../adaptive-environment-generation/README.md) records this process
and preserves each source-level result before the representation is revised.
