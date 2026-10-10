# Mathematics

Mathematics is the first experimental domain in Anarres. Deterministic verification lets us measure how policy-relative learning signal, generated cost, model scale, and compute budget jointly shape RL utility.

The program asks one question across different mathematical and formal-reasoning settings:

> Given a starting policy and a compute budget, which training environment will produce the greatest improvement on a held-out target?

## Studies

| Study | Candidate environments | Held-out target | Purpose |
| --- | --- | --- | --- |
| [Environment utility across model scale](environment-utility/README.md) | Four controlled OpenR1-Math distributions constructed separately for each starting policy | A fixed, disjoint OpenR1-Math panel, with an independent mathematical sensitivity panel | Establish whether pre-RL measurements predict utility across model scale and generated-token budget |
| [Environment utility for VeriBench](veribench/README.md) | Training environments assembled for Lean 4 formal code verification | Held-out VeriBench tasks | Test whether the same measurement approach can identify environments that improve a distinct formal-verification target |

The first study establishes the predictive relationship in a controlled setting. The VeriBench study changes the candidate environments and the held-out target while preserving the central environment-utility question. Its measurements must be collected under the new policy, verifier, and task distribution before downstream training outcomes are inspected.

The environment types are intentionally different. The controlled study uses fixed distributions of answer-producing mathematical prompts under one symbolic verifier. VeriBench environments contain program-to-Lean tasks in which an agent must use tools, construct a formal artifact, and satisfy checks for compilation, meaningful specifications, and theorem coverage. This provides a stronger test of whether environment-utility measurements remain predictive when the interaction and verification structure changes.

Citation guidance will be added with each citable research release.
