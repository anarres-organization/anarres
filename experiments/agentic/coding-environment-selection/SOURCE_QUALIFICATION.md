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

## Retrospective bridge additions

**CodeMidas** provides one four-arm training decision evaluated on SWE-bench Pro, DeepSWE, and CodeMidas Val. All arms share the training configuration and checkpoint range. The comparison varies both task quality and scale: verified pools contain 1K, 3K, or 5K tasks, while the 8K vanilla pool omits cleaning, execution-consistency checks, and post-rollout filtering. The bridge treats the three evaluations as nested endpoints of one decision.

**SWE-Gym-Verified** provides four 512-task environments, three training seeds, and two held-out evaluations. Clean and Orig match size and starting difficulty, while Orig+Filter is easier and remains a negative control for pass-rate selection. The execution-backed audit status is known before training. The two evaluations remain nested under one training experiment.

**EnvSched** provides four model-scale decisions under one EnvScaler task pool, common rollout budgets, and fixed optimization settings. BFCL-v3, tau-Bench, and ACEBench-Agent are nested endpoints within scale. EnvSched is an online allocator rather than a pre-RL selector, so its panels test whether reward differentiation and environment coverage remain useful after training begins.

The complete bridge contains seven sources, 14 independent training decisions, 27 endpoint panels, and 104 candidate-endpoint rows. It uses only within-panel ordering and normalized regret. The practical rule reaches 76.9% pair ordering and 0.017 normalized regret, compared with 50.0% and 0.529 for an uninformed tie. This is retrospective support for the measurement framework, not a fitted universal selector.

## Regression-risk evidence

SWE-Gym-Verified releases every held-out attempt from four training environments, three seeds, and 1,035 tasks. Averaging each task across seeds gives 4,140 task-environment outcomes and 476 pass-rate decreases of at least 25 points. A logistic model uses starting-policy task success, target shift, and execution-backed reward-audit status, all known before training. Leave-one-repository-out evaluation across 22 repositories reaches 0.736 ROC AUC and captures 41.8% of regressions in the highest-risk 20% of outcomes. Starting behavior alone reaches 0.638 AUC and captures 15.1%. A repository-clustered bootstrap places the AUC improvement in [0.045, 0.127].

The benchmark-level seed table provides a complementary view. Its five regressions relative to the common starting model all occur on the shifted SWE-bench Pro target after training on unaudited labels. Both analyses were reconstructed after publication. They support source-contained regression triage and require transfer to a new coding intervention before prospective use.

## Mechanism evidence

**EnvSched** reallocates training online using reward differentiation and coverage. It enters only the adaptive bridge block and is not treated as a pre-RL selection result.

**RepoFactory** tests validity repair, implementation scope, and structural coupling when constructing repository environments. It is a post-freeze external mechanism check, not a prospective test of the released selector.

**River** compares its filtered 3.5K pool with a random 3.5K TMax subset across four benchmarks and three seeds. The full River recipe leads on three benchmarks and on the reported mean. Because the comparison also includes River's behavior-shaping recipe, it supports verifier integrity as a mechanism but does not isolate environment selection.

Broader studies remain in the source registry as landscape context. SETA, LegoEnv, and Endless Terminals provide evidence about construction, validation, difficulty evolution, and scaling. Their policies, budgets, outcome definitions, or intervention units are too heterogeneous for the exact panel comparison.

## Qualification boundary

A general terminal selector is not qualified. Qualification would require additional prospectively frozen, source-separated decisions, multiple training seeds, independently assembled candidate sets, and a demonstrated gain over reward information alone. The current result qualifies a reproducible measurement and evaluation path and shows that policy-aligned progression transfers as an ordering principle in two additional public studies.
