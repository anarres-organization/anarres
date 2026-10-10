# Environment utility for VeriBench

**Status:** Study design in progress.

[VeriBench](https://ehersch.github.io/veribench-blog/) evaluates whether AI coding agents can translate programs into meaningful Lean 4 artifacts with checkable specifications and theorems. This workstream studies a different question about the same target: which training environments produce the greatest held-out improvement on VeriBench at a fixed RL budget?

It extends the [controlled environment-utility study](../environment-utility/README.md) to a new candidate family and evaluation target. Candidate environments are assembled for formal code verification, measured under the starting policy, and compared through their downstream VeriBench utility curves. The goal is to predict which environments will help before paying for full RL runs.

## Why this is a new environment setting

| Component | Controlled scale study | VeriBench study |
| --- | --- | --- |
| Training tasks | Natural-language mathematical problems with answer generation | Programs that must be translated into structured Lean 4 artifacts |
| Interaction | One response followed by symbolic answer verification | Agentic tool use, Lean compilation, specification construction, and proof development |
| Reward evidence | Mathematical equivalence under one deterministic verifier | Compilation, nontrivial formal content, and coverage of the intended specification |
| Held-out target | Pass@1 on a disjoint OpenR1-Math panel | Performance on held-out VeriBench tasks |

These differences can change which experience is available, how much survives the training contract, and what counts as useful downstream improvement. The VeriBench study therefore remeasures every candidate environment under its own starting policy and tests the predictive representation again. The original four cells and fitted coefficients remain specific to the controlled scale study.

## Planned protocol

1. Freeze training candidates and a held-out VeriBench evaluation split by content identity.
2. Qualify Lean toolchains, task fixtures, and reward behavior before measuring learnability.
3. Measure policy-relative signal, effective coverage, generated cost, and verifier reliability without reading RL outcomes.
4. Freeze environment predictions and uncertainty rules.
5. Train the selected candidate environments under one compute-matched contract.
6. Score curve prediction, environment ordering, and allocation regret on held-out VeriBench performance.

The protocol keeps infrastructure failures separate from scientific failures and records every environment identity before claim-bearing training. Public task releases will use versioned external artifacts with dataset cards and immutable revisions.
