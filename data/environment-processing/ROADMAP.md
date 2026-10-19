# Environment-processing implementation plan

This plan turns the existing CPU reference path into a reproducible system for constructing and validating RL environment banks. It is intentionally limited to public scientific work: stable data contracts, reusable processing, explicit validation gates, and released evidence.

## Objective

Given a versioned task collection, starting policy, rollout contract, and target evaluation, produce candidate environments whose identities, validity, policy-relative measurements, overlap, and provenance can be audited before expensive RL begins.

The processor prepares and measures candidates. It does not choose a claim-bearing environment after reading its downstream training outcome.

## Current baseline

The repository already provides a small end-to-end reference path:

- [x] explicit `admitted`, `reserve`, `repair`, and `quarantine` outcomes
- [x] separate infrastructure validity, verifier validity, and scientific reward
- [x] usable signal density ρ and normalized effective coverage H
- [x] content-addressed environment manifests
- [x] versioned JSON Schemas and a CPU-only golden-path example

This baseline fixes the scientific interface. The remaining work expands source coverage, reliability measurement, candidate construction, and prospective validation without weakening those invariants.

## Phase 1: source qualification

Build deterministic adapters for at least two public task sources or source families.

Deliverables:

- pinned source revisions, licenses, and stable task identities
- deterministic normalization and deduplication
- fixture, resource, oracle, no-op, and repeated-verifier checks
- versioned export into an executable task format where the source requires one
- structured exclusion records for contamination, verifier defects, and infrastructure failures

Exit criteria:

- fixture outcomes reproduce at least 95% of the time under the frozen validation contract
- a retry cannot change task identity or reinterpret infrastructure failure as reward zero
- every admitted task can be traced to its source revision and transformation record

## Phase 2: policy-relative measurement

Add resumable probes under an explicitly versioned policy and rollout contract.

Deliverables:

- grouped rollout records with generated-token and admission accounting
- at least two independent measurement views
- per-task contributions to ρ and H
- reliability intervals and failure summaries
- content-addressed probe outputs that can resume without duplicating completed work

Exit criteria:

- every promoted coordinate reports independent-view reliability
- incomplete groups and infrastructure-invalid sessions are excluded by explicit rules
- the probe can be reproduced from its model, task, verifier, sampling, and budget identities

## Phase 3: candidate construction

Construct environment mixtures from the qualified, measured task bank without consulting claim-bearing RL outcomes.

Deliverables:

- unique-task, source-diversity, verifier-diversity, and cost constraints
- pairwise overlap and target-contamination audits
- coordinate-geometry diagnostics for ρ and H
- deterministic mixture manifests and exclusion reasons
- a compact development partition and an untouched prospective partition

Exit criteria:

- pairwise overlap is measured and bounded before training
- selected candidates span useful variation without relying on nearly redundant coordinates
- task identities, mixture weights, partitions, and construction rules are frozen and hashed

## Phase 4: independent confirmation

Re-measure the frozen finalists with a new rollout seed while preserving failed and infrastructure-invalid observations.

Deliverables:

- construction-versus-confirmation reliability reports
- coordinate uncertainty and abstention rules
- immutable environment and measurement manifests
- a signed freeze record for the downstream experiment

Exit criteria:

- confirmation cannot swap candidates or tune construction thresholds
- discrepancies remain visible and alter uncertainty rather than being silently discarded
- the full pre-RL packet passes schema, identity, integrity, and provenance checks

## Phase 5: downstream validation

Run a small, prespecified RL panel to test whether the processed measurements support useful environment decisions.

The primary analyses should distinguish:

- held-out utility-curve error
- pairwise ordering and best-environment decisions
- allocation regret against simple operational baselines
- uncertainty coverage
- training-seed variation and infrastructure failure rates

The first public validation targets are one mathematical reference panel and one executable agentic reference panel. A result can validate the processing system without establishing a universal utility law.

## Release gate

A reference release is complete only when it includes:

- source and task identities with licenses and hashes
- qualification, probe, and candidate-construction manifests
- development and prospective partitions
- scripts that regenerate reported tables and figures from identified inputs
- explicit exclusions and limitations
- no credentials, machine-specific paths, transient logs, checkpoints, or mutable artifact aliases

## Non-goals

The current plan does not generate new tasks, infer utility from pass rate alone, automatically select the final training environment, or promote additional coordinates without independent predictive evidence. It also does not prescribe a new rollout or RL runtime when an existing maintained system satisfies the frozen scientific contract.
