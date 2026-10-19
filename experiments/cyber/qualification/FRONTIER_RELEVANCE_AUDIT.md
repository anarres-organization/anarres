# Frontier relevance audit

Date: 2026-10-17

This audit answers one narrow question: which current cyber capabilities retain
meaningful frontier headroom, and which public benchmarks measure them? It does
not determine which benchmark is scientifically eligible for the pilot.

## Official evidence

| Release or study | Official evidence | Relevant result |
| --- | --- | --- |
| [GPT-6 Astra](https://openai.com/index/gpt-6-astra/) | Official model report | Historical ExploitBench 100%; ExploitGym 42.4%; June--August 2026 ExploitBench internal port 39.0%; SEC-Bench Pro 85.4% |
| [GPT-6 Astra system card](https://deploymentsafety.openai.com/gpt-6-astra/vision) | Official protocol detail | ExploitGym v1 uses 869 tasks, an offline environment, and intended-vulnerability judging; SEC-Bench Pro uses the May 2026 183-task V8/SpiderMonkey set with an amended root-cause procedure |
| [Anthropic exploit-evaluation study](https://www.anthropic.com/research/exploit-evals) | Official research report | ExploitGym spans patched userspace, V8, and Linux vulnerabilities and was developed with contributions from researchers at Anthropic, OpenAI, and Google |
| [CyberGym-E2E](https://www.cybergym.io/cybergym-e2e/) | Official benchmark report | 920 tasks across 139 projects with cumulative discovery, proof-of-concept, patch, functionality, and target-fix stages |
| [MiMo-V2.6](https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL/blob/main/MiMo_V2_6_technical_report.pdf) | Open-weight technical report | CyberGym, SEC-Bench Pro, ExploitGym, ExploitBench |

Two scores obtained with different agent loops, tool budgets, contexts,
mitigations, or grading revisions are not automatically comparable. The values
above establish that a capability is relevant and has headroom under the stated
contract; they are not local baselines.

The 39.0% recent-ExploitBench value is the headline table entry in the Astra
model report. System-card passages describe additional exploit rates under more
specific conditions. Because the underlying task set is internal and the
presentations do not expose a locally reproducible denominator and artifact,
this plan uses the result only as evidence for recency and sequestering. It does
not use 39.0% as a calibration target or cross-system comparison.

The benchmark maintainers provide a second relevance signal. CyberGym's current
submission protocol requires both success and cost reporting because the most
capable systems are approaching saturation. SEC-Bench Pro exposes 344 verified
V8, SpiderMonkey, and Linux cases and records its use in recent frontier
evaluations. These facts make both candidates relevant, while also strengthening
the need to measure headroom for the exact 8B starting policy.

## Consequence for the roadmap

The evidence separates training-family qualification from frontier-facing
evaluation.

- CyberGym remains attractive for its large real-vulnerability reservoir. Its
  identity overlap, storage, leakage, and exact warm-start headroom must be
  resolved empirically.
- SEC-Bench Pro remains attractive for its verified cases, explicit artifacts,
  and current frontier use, but an 85.4% frontier score limits its value as the
  sole external endpoint. The first pass is limited to V8 and SpiderMonkey;
  Linux is deferred because KVM and privileged execution add infrastructure
  that is unnecessary for the benchmark-selection question.
- ExploitGym is the priority public external transfer target because the
  strongest published result is 42.4%. Its broader execution stack remains off
  the first bakeoff's critical path.
- Historical ExploitBench remains a graded diagnostic rather than a frontier
  endpoint because the strongest published result is 100%.
- The recent internal ExploitBench port establishes the value of recency but is
  unavailable as a reproducible target. A later sequestered panel needs a
  prospective timestamp and independent identity audit.
- CyberGym-E2E warrants a bounded investigation as an end-to-end defensive
  target. It is not silently added to the first integration workload.

The benchmark decision therefore remains evidence-driven: relevance is a hard
eligibility gate, while containment, verifier fidelity, measurable signal,
precision, and bounded cost decide whether a candidate can support RL. A
benchmark can pass the relevance gate as an external target while failing the
learnability gate as a training source.

## Frontier capability-gap registry

Before every target freeze, record:

- source and report date;
- model and access regime;
- benchmark and task revision;
- harness, tool, context, token, time, and mitigation contract;
- primary metric and score;
- historical-exposure or recency status;
- proposed role: training candidate, internal target, or external transfer;
- local warm-start floor and feasibility status when measured.

The registry is re-audited before a new protocol version and at least quarterly
while an experiment remains unlaunched. A score change can trigger re-audit, but
cannot redesign a frozen experiment.

## Re-audit rule

At every new protocol version, record the report date, benchmark revision,
metric, scaffold, context and tool budget when the official source provides
them. A newer leaderboard score may motivate re-audit, but it cannot change a
frozen experiment or substitute for a local qualification measurement.
