# External landscape audit

Date: 2026-10-19.

This audit records published cybersecurity-benchmark evidence as **eligibility
and headroom context only**. It makes **no numeric claim** about the local
Nemotron-8B warm start. Scores produced by other models under other scaffolds
are not local baselines; per the frontier-relevance rule, appearing in a report
establishes relevance and headroom, not comparability. The family and target
choice in `qualification-protocol.v2.json` is justified by the capacity gate and
the disjoint-identity design, not by any score below.

## Benchmarks

| Benchmark | Venue | Task / outcome | Published headroom signal | Role in v2 |
| --- | --- | --- | --- | --- |
| CyberGym | ICLR 2026 | PoC reproducing a vuln from description + codebase; 1,507 vulns / ~188 projects; ARVO -> OSS-Fuzz Docker images; Apache-2.0 | best agent ~20% (OpenHands+Sonnet-4 17.9%; GPT-5+thinking 22%); later scaffolds reported 50-66%; SWE-specialized models <= 2%; a 35B *base* model ~9.75% | Primary: in-domain training pool + isolated target |
| SEC-bench / SEC-Bench Pro | NeurIPS 2025 | Auto-built CVE PoC-gen + patch; V8+SM ~207 verified cases | best code agents ~12.5% | Rejected as target (capacity); optional external transfer |
| ExploitGym | arXiv 2605.11086 | Turn crashing input into working exploit; 898 instances (userspace/V8/Linux) | strongest frontier models exploit a meaningful share; reported sandbox-escape incidents | Later external frontier-transfer target |
| CyberGym-E2E | ICML 2026 | discover -> PoC -> patch -> functionality; 920 tasks / 139 projects, cumulative stages | ~80% patch-when-told; end-to-end much lower (discovery is the wall) | Later end-to-end investigation |
| Cybench | ICLR 2025 | 40 professional CTF tasks | solves only easiest; no small-model data | Scaffold sentinel |
| NYU CTF Bench | NeurIPS 2024 | CTF with tool-calling | limited | Coverage/diversity |
| CTF-Dojo | NeurIPS 2025 | 658 Dockerized CTF challenges (pwn.college); SFT trajectories released; RL = future work | best 32B 31.9% Pass@1; +11.6pp on InterCode/NYU/Cybench | Optional cross-domain challenger |
| Random-Crypto | arXiv 2506.02048 | Procedural crypto CTF; GRPO on Llama-3.1-8B; code released | transfers to picoCTF | Optional cross-domain challenger |

## Warm-start availability

No public off-the-shelf warm-start SFT spans the four-scale ladder (1.7B/4B/8B/14B)
for cyber or terminal work. Closest public points: Tmax (Qwen3-8B only, terminal),
OpenThinkerAgent-8B (coding cold-start), and a tool-calling SFT-vs-RL study across
Qwen3 0.6B-14B (function-calling, not terminal/cyber). This is why v2 pins the
agentic Nemotron-8B warm start for the pilot and defers any multi-scale ladder to
the powered study as a separate project. CTF-Dojo's released SFT trajectories are
NOT adopted as the warm start: doing so would entangle the warm start with a
training family (leakage).

## Consequence for the pilot

- CyberGym is relevant (frontier headroom), reproducible (Apache-2.0, ARVO/OSS-Fuzz
  Docker), and large enough to split into a training pool and a >= 246-task target
  at project granularity -> eligible as primary family.
- The low published rates for small/base/SWE-specialized models are consistent
  with a real floor risk for an 8B warm start. v2 does not convert this into a
  number; the floor is measured in Phase C, and the frozen reliability simulation
  (`reliability_oc.json`) already shows the two-view / 48-task design can reliably
  measure only at per-task success >= 0.30, which sets the rollout/abstention rule.

## Capability-gap registry fields (to record at each target freeze)

source and report date; model and access regime; benchmark and task revision;
harness/tool/context/token/time/mitigation contract; primary metric and score;
historical-exposure or recency status; proposed role; local warm-start floor and
feasibility status when measured.

## Sources

- CyberGym: arXiv 2506.02548; rdi.berkeley.edu/blog/cybergym
- ExploitGym: arXiv 2605.11086
- SEC-bench: arXiv 2506.11791
- CyberGym-E2E: arXiv 2606.04460; rdi.berkeley.edu/blog/cybergym-e2e
- Cybench: ICLR 2025 (reglab.stanford.edu)
- NYU CTF Bench: NeurIPS 2024
- CTF-Dojo: arXiv 2508.18370
- Random-Crypto: arXiv 2506.02048 (crypto RL)
