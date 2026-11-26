# Source qualification

The released comparison admits a source only when candidate environments share a starting policy, training recipe, budget, and held-out evaluation within that source. Native scores remain within study. The analysis never treats endpoints from different studies as one performance scale.

## Claim-bearing panels

**TMax** compares seven public terminal-training pools under one Qwen3.5-35B-A3B recipe and common Terminal-Bench evaluations. Candidate measurements were reconstructed without using the published outcome table, but the paper already existed. This is an outcome-blind shadow decision rather than a prospective experiment. The exact historical starting revision was unavailable, which limits claims about measurement fidelity.

**RLVE** provides six mixtures of 16 verifiable environments under one pinned 1.5B policy and common training contract. The selector and candidate measurements were frozen before the claim-bearing outcomes were opened. This is the prospective panel. It has one training seed, and the two reported updates are nested endpoints of one decision.

Together these sources provide two independent training decisions and four nested endpoints. They do not provide four independent replications.

## Source-separated external check

**AutoEnvScaling** provides four matched model-by-proposer decisions under held-out Terminal-Bench 2.1 evaluation. Within each decision, static TMax and AutoEnvScaling use the same proposer and matched training steps. A source-native rule prefers environments that are validated and calibrated against the current policy and use its trajectories and failures. It selects the reported best candidate in all four decisions and orders all six forecasted pairs correctly. Static TMax has 5.45 points of mean regret.

**Environment Evolution** provides two matched three-way comparisons under a fixed synthesis model and equal environment count. The source-native rule prefers its verified progressive lineages and reward-threshold scheduler. It selects the reported best process for both Qwen3.6 solvers and orders all four candidate pairs correctly. Static environment ensembles have 11.8 points of mean regret.

Both checks were reconstructed after publication. They test whether the earlier signal, verifier-integrity, and coverage principles transfer to new sources, but they are neither prospectively frozen forecasts nor a cross-study fit. Scores remain inside each study and are reported separately from the TMax and RLVE panels.

## Mechanism evidence

**EnvSched** reallocates training online using reward differentiation and coverage. It informs the adaptive stage of environment design but is not pooled with pre-RL selection.

**RepoFactory** tests validity repair, implementation scope, and structural coupling when constructing repository environments. It is a post-freeze external mechanism check, not a prospective test of the released selector.

**River** compares its filtered 3.5K pool with a random 3.5K TMax subset across four benchmarks and three seeds. The full River recipe leads on three benchmarks and on the reported mean. Because the comparison also includes River's behavior-shaping recipe, it supports verifier integrity as a mechanism but does not isolate environment selection.

Broader studies remain in the source registry as landscape context. CodeMidas, SETA, Environment Evolution, LegoEnv, and Endless Terminals provide evidence about construction, validation, difficulty evolution, and scaling. Their policies, budgets, outcome definitions, or intervention units are too heterogeneous for the exact panel comparison.

## Qualification boundary

A general terminal selector is not qualified. Qualification would require additional prospectively frozen, source-separated decisions, multiple training seeds, independently assembled candidate sets, and a demonstrated gain over reward information alone. The current result qualifies a reproducible measurement and evaluation path and shows that policy-aligned progression transfers as an ordering principle in two additional public studies.
