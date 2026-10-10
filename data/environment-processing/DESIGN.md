# Environment-processing design

## Goal

Build a reusable pipeline that turns existing task sources into standardized, verified, and policy-measured RL environment banks. The pipeline automates acquisition, qualification, measurement, and candidate construction while leaving the final experimental choice explicit and reviewable.

## Concrete example

Consider 10,000 coding tasks drawn from repository repair, shell use, and notebook debugging for an 8B policy.

| Task | Observation | Processing decision |
| --- | --- | --- |
| A | The oracle passes, the no-op fails, 6 of 16 policy rollouts succeed, and infrastructure is stable. | Admit the task. Record reward variation, generated tokens, admitted advantage mass, and source metadata. |
| B | The oracle passes, but all 16 policy rollouts succeed. | Keep the task in a policy-relative reserve. It is valid but provides no group-relative signal under this rollout contract. |
| C | The oracle fails or a no-op receives reward 1. | Quarantine the task as a verifier defect. Do not reinterpret the failure as policy reward 0. |
| D | The verifier is correct, but 5 of 16 sessions fail because the image cannot start. | Mark the task for repair and retry it under the same identity after the infrastructure issue is fixed. |
| E | The task is valid and mixed but nearly duplicates a held-out benchmark task. | Exclude it from training and preserve the contamination record. |

The result is not one opaque “good dataset.” It is a task bank with explicit admitted, reserve, repair, and quarantine states, together with versioned candidate mixtures.

## Policy-relative measurements

For each candidate environment E, the probe computes:

```text
ρ(E) = 10⁶ × total admitted advantage mass / generated action tokens

H(E) = effective number of prompts carrying admitted mass / prompt count
```

ρ measures usable group-relative signal per million generated action tokens. H measures how broadly that usable signal is distributed across prompts. Candidate construction should create meaningful variation in both coordinates without making them redundant. Low correlation is a panel-level design objective, not a task-level admission rule.

## Pipeline

1. **Acquire and normalize.** Pin source revisions and licenses, assign stable task identities, deduplicate, and convert tasks through source adapters.
2. **Validate fixtures and verifiers.** Check schemas, buildability, resource declarations, oracle success, no-op failure, and repeated verifier stability.
3. **Probe the target policy.** Run a frozen rollout contract with configurable group size and independent measurement views. Record success, mixed-group probability, generated cost, admission, coordinate contributions, and failure modes.
4. **Construct candidate environments.** Build mixtures with enough unique tasks, bounded overlap, source and verifier diversity, variation in ρ and H, and explicit cost and reliability limits.
5. **Confirm and freeze.** Re-measure finalists with an independent rollout seed. Freeze manifests only when integrity checks and reliability gates pass.
6. **Validate with RL.** Train a prespecified panel and test whether the measurements predict held-out utility curves, rankings, and allocation regret.

## Implementation strategy

The reference implementation begins in Python so scientific contracts can evolve quickly. Once schemas and gates stabilize, CPU-intensive catalog operations can move to Rust without replacing Python model inference, Harbor adapters, or existing RL runtimes.

Every command should be resumable, content-addressed, and idempotent. Outputs should use versioned JSON or Parquet schemas with provenance, hashes, exact contracts, and explicit error taxonomies.

## Initial milestones

1. Define source, task, verifier, rollout, and environment schemas.
2. Implement two source adapters with stable identities, provenance, deduplication, and oracle/no-op gates.
3. Add resumable policy probing with two independent measurement views.
4. Produce candidate mixtures with coordinate, overlap, source-diversity, and reliability audits.
5. Validate a compact development and prospective panel with downstream RL.

## Success criteria

- At least two source families or domains are supported.
- Fixture outcomes reproduce at least 95% of the time.
- Infrastructure failures never become scientific reward zero.
- Every promoted coordinate includes an independent-view reliability estimate.
- Candidate overlap is measured and bounded.
- The constructed panel spans useful, nonredundant variation in ρ and H.
- Outputs integrate directly with training and evaluation systems through versioned manifests.

## Non-goals

The first release will not generate new tasks, treat moderate pass rate as sufficient evidence of utility, choose final environments automatically, or change filters after observing claim-bearing outcomes. Additional coordinates may be evaluated as challengers, but they become required only after independent predictive evidence.

## Starting references

- [DataComp-LM](https://arxiv.org/abs/2406.11794) for controlled filtering and mixing under fixed training contracts
- [DAPO](https://papers.nips.cc/paper_files/paper/2025/file/a4277440d50f1f15d2cb4c14f7e0c0d2-Paper-Conference.pdf) for zero-variance group filtering and dynamic refill
- [Uni-Agent](https://github.com/XiaomiMiMo/uni-agent) for scalable, traceable agent rollouts and RL integration
- [Harbor](https://github.com/harbor-framework/harbor) for executable task and verifier contracts
- [RLVE](https://arxiv.org/abs/2511.07317) for policy-adaptive difficulty and environment scaling
- [Mathematics](../../experiments/mathematics/README.md) for policy-relative environment measurements and finite-budget utility prediction
