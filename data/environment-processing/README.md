# Automated environment processing for high-fidelity RL

This project converts heterogeneous task collections into standardized, verified, and policy-measured RL environment banks. It is designed to make candidate construction cheaper, more reproducible, and easier to extend across domains before large RL runs begin.

An executable task can be unusable even when its prompt looks reasonable. The sandbox may be broken, the oracle may fail, a no-op may receive reward, or the current policy may almost always succeed or fail. Individually valid tasks can also form a weak environment when candidate mixtures overlap heavily or when their measured properties become redundant.

## Processing path

```text
acquire and normalize
    → validate fixtures and verifiers
    → probe the target policy
    → construct candidate environments
    → independently confirm finalists
    → freeze identities and contracts
    → validate predictions with RL
```

The system distinguishes infrastructure failure from scientific reward zero at every stage. Each task retains its source revision, license, stable identity, transformation history, verifier result, exclusions, and content hashes.

## Task states

| State | Meaning |
| --- | --- |
| `admitted` | The fixture and verifier pass, infrastructure is valid, and policy rollouts contain reward variation. |
| `reserve` | The task is valid but its rollout group has no relative signal for the current policy and contract. |
| `repair` | A sandbox, image, harness, or missing-output failure prevents scientific interpretation. |
| `quarantine` | The oracle fails, a no-op passes, or another verifier defect invalidates the task. |

The first reference implementation already exposes this distinction and computes the ρ and H environment coordinates from a frozen probe:

```bash
make example
```

## Outputs

The complete pipeline will produce:

1. versioned task-bank manifests with pinned source and image hashes
2. task-level integrity, resource, rollout, and provenance records
3. reproducible candidate-environment manifests
4. reports covering signal, coverage, cost, reliability, overlap, and exclusions

Final scientific selection remains explicit. The processor prepares environments and measures their properties. It does not silently optimize a panel against downstream RL outcomes.

## Design

The [design document](DESIGN.md) specifies the concrete filtering example, measurement contract, implementation strategy, initial milestones, and success criteria. The original [project proposal](project-proposal.pdf) is also included.

## Current implementation

- `anarres.environments.qualification` classifies probe groups using explicit fixture, verifier, infrastructure, and reward-variation outcomes.
- `anarres.environments.metrics` computes usable signal density ρ and normalized effective coverage H.
- `anarres-env probe` converts a frozen policy-probe record into a content-addressed environment manifest.
- JSON Schemas define probe inputs and environment manifests.

The next implementation layer adds source adapters, deterministic acquisition, deduplication, multi-view reliability, candidate construction, overlap audits, and independent confirmation.
