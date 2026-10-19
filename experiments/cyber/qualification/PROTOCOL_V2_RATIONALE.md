# Protocol v2 rationale and freeze receipt

Date frozen: 2026-10-19. No warm-start or RL outcome has been observed for cyber.
This document records why `qualification-protocol.v2.json` supersedes v1. It is a
declared **scientific-design change**, not outcome tuning: every change below is
justified by the frozen artifacts, an a-priori simulation, or published external
facts, never by a measured cyber success rate.

## Why v2 at all

An adversarial review of the v1 plan surfaced one fatal confound and several
specification gaps. v1 is internally consistent but, read against
`experiments/cyber/README.md`, it left the first utility contrast
uninterpretable and two gates under-specified. v2 fixes these before any fixture
is materialized, which is the only honest time to change a protocol.

## Changes and their justification

### 1. CyberGym supplies both the training pool and the target (fixes the confound)

The scientific object is `U(E, pi0, C, D)` = improvement on target `D` from
training on environment `E`. A plan that trained on CTF-style tasks and
evaluated on CyberGym real-vulnerability tasks would mix two different
capabilities, and the README (the "distinct scientific outcomes ... must not be
pooled" rule) forbids exactly that. If cross-domain transfer were near zero, an
environment-selection null would be uninterpretable: we could not separate "the
predictor was wrong" from "nothing in a CTF family moves a real-vulnerability
target."

v2 therefore makes both `E` and `D` CyberGym real-vulnerability tasks, split by
the disjointness standard below. The 4-6 pilot environments are **constructed
within** the CyberGym training pool by varying interpretable controls, which is
the README-sanctioned environment-construction prototype. This mirrors the
mathematics study, where training and evaluation were the same domain.

### 2. The disjointness standard is identity-level, not CVE-level

Splitting one benchmark is only interpretable if train and target share no
hidden identity. CVE/repo/near-duplicate disjointness is necessary but not
sufficient. v2 requires disjointness across exact task, **upstream project and
fork lineage**, **patch / root-cause equivalence class**, code near-duplicate,
**vulnerability class + sanitizer signature**, **shared fuzz-harness source**,
and **ARVO/OSS-Fuzz provenance**. It also requires a **memorization/temporal
audit** of the target partition against the Nemotron-8B knowledge cutoff: a CVE
disclosed before that cutoff may leak through the base model and contaminate the
target independent of training. The shared verifier and submission service are
the measurement instrument, not a confound, and are exempt.

### 3. Capacity is measured at project granularity

The `>= 246` target-panel minimum (from `POWER_ANALYSIS.md`) must hold at the
level on which we split. CyberGym's ~1,507 tasks derive from a far smaller number
of upstream projects (published as ~188). A project-disjoint split must still
yield >= 246 target tasks **and** leave a training pool able to produce 4-6
genuinely distinct environments. The distinct-project and distinct-patch-class
counts are computed at Phase-B materialization (they are not derivable from the
public code repo alone); 188 projects is the planning figure. SEC-Bench Pro
V8+SpiderMonkey (~207 verified cases: 103 V8 + 104 SM per `STATIC_SOURCE_AUDIT.md`)
fails this gate and is formally rejected as the target.

### 4. Warm start is the pinned agentic policy at a single scale

v1 pins `nvidia/Nemotron-Terminal-8B` with `require_exact_match_to_agentic_warm_start`.
Cyber is the second domain test after agentic terminal work and must reuse the
**same** starting policy so cross-domain comparison is valid. v2 keeps this and
pins the pilot to the single 8B scale. The multi-scale ladder (needed only for
the fit-through-8B / predict-larger extrapolation) is deferred to the powered
study as its own budgeted project; no public warm start spans Qwen3 1.7B-14B for
this domain, so treating the ladder as a pilot line item would hide a large cost.

### 5. Reliability thresholds unchanged; an a-priori simulation sets budget and abstention

v2 does **not** loosen the reliability gate. `reliability_oc_sim.py` (frozen,
output in `reliability_oc.json`) sweeps per-task success 0.02-0.40 **without
assuming the starting policy's rate** and reports how often two independent G=8
views agree within the frozen thresholds when the true coordinates are identical.

Result: with the frozen two-view / 48-task design, the full reliability gate
agrees >= 80% of the time only at per-task success **>= 0.30**. At ~5% success
the rho-agreement gate is near a coin flip (~0.51) from sampling noise alone.
The honest consequence is a budget/abstention rule, not a weaker bar: if the
observed regime is below the reliably-measurable floor, increase rollouts or
return `UNMEASURABLE`. This also quantifies the floor risk the external audit
raised.

### 6. Narrowed claim and a construction-control gate

Because the environments are now control-variations within one pool, the pilot
tests "which control-varied environment best improves the target," not "which
benchmark family." v2 states this narrower claim and adds a gate that
construction controls must be target-agnostic and audited against the target
partition, with a fallback (disjoint source strata or difficulty bands) if
constructed controls are not genuinely distinct.

### 7. Single frozen ordering for both partitions

The modified `freeze_development_candidates.py` must draw the 48-task probe
subset and the `>= 246`-task target partition from **one** salted ordering, make
them mutually exclusive, exclude probe tasks from the target, and preserve both
by content hash before any measurement.

## Effect rule: pinned, not moved

The expansion rule keeps v1's values exactly: minimum absolute environment
contrast 0.08, two-seed same-sign, and the paired task-cluster interval
excluding zero. v2 only restates the target effect as a true effect and names
the cluster interval as the evidence rule; no threshold moves.

## What is still blocked

`execution_authorized` remains false. Phase C (the model-based floor probe) runs
only after Phase B containment and oracle/no-op/reset checks pass. Phase C output
is never an RL authorization; it is one of: proceed to qualification, external-
target-only, or unmeasurable.
