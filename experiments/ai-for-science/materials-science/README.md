# Predictable post-training for atomistic models

Equal-size atomistic datasets can produce different physical outcomes. This
program asks whether measurements made before post-training can predict which
environment will improve a specified model, physical target, and compute
budget.

## Start here

Install the native CLI and materials adapter from a repository checkout:

```bash
cargo install --path crates/anarres-cli --locked
uv tool install ./experiments/ai-for-science/materials-science/mlip-phonon-environment-selection/adapter
anarres adapter doctor materials
anarres materials status --repository .
```

Run the released checks with:

```bash
make materials-check
```

The command verifies the supervised phonon release, retrospective bridge, and
MLIP study. Model training and phonon simulation use separate environments and
are not installed with the CLI.

## Evidence at a glance

| Study | Status | Result |
| --- | --- | --- |
| [Supervised phonon selection](phonon-environment-selection/) | Complete | The frozen signal-plus-coverage rule missed the best candidate at all three PBE budgets. |
| [Independent PBEsol transfer](phonon-environment-selection/pbesol-transfer/) | Complete | The transferred ordering selected the best candidate at two of three budgets; no candidate improved absolute Top-100 stability over the starting checkpoint. |
| [Retrospective bridge](retrospective-bridge/) | Validated | Sixteen public studies provide 804 matched decisions and 3,002 candidate arms. The harm audit reaches 0.708 source-macro ROC AUC and identifies 41.8% of adverse choices in the highest-risk 20%. |
| [MLIP phonon study](mlip-phonon-environment-selection/) | Prospective test scored | The learned signal-density selector missed the best environment at all four budgets. Deterministic baselines selected it, and the post-test audit identifies unsupported extrapolation as the main failure. |

These results are useful because they include failures. The released evidence
does not support a universal materials-data selector. It shows which
measurements transfer, where they fail, and how the next prospective decision
must be constrained.

## Current research boundary

The MLIP experiment uses 16 environments matched on atom and graph-edge budget:
12 for development and four for a prospective test. Development results favored
a signal-density predictor, but its frozen choice extrapolated beyond the
development support and ranked last prospectively. The next experiment must
expand support and freeze an abstention rule before another candidate family is
opened.

The scientific object is

$$
U(E,\pi_0,C,D)=P(\pi_{E,C};D)-P(\pi_0;D),
$$

where $E$ is a distribution over atomic configurations, $\pi_0$ is the common
starting potential, $C$ is the matched training or labeling budget, and $D$ is
the frozen physical target. Environment utility is always tied to those four
parts of the contract.

## Why materials require a distinct contract

An atomistic configuration may contribute an energy, forces for every atom,
and a stress tensor. Frames from one relaxation trajectory are correlated, and
downstream behavior depends on chemistry, geometry, strain, force regime, and
level of theory. Low average energy or force error does not guarantee reliable
phonons, barriers, defects, dynamics, or stability decisions.

The workflow therefore keeps the physical target fixed:

```text
starting potential + physical target + compute budget
    -> qualify sources, labels, units, and reference calculations
    -> measure candidate configuration distributions
    -> freeze the decision rule and candidate environments
    -> fine-tune under matched budgets
    -> evaluate on a disjoint physical target panel
    -> score prediction and selection quality
```

Material identity is separated before trajectory frames are sampled. Exact
structures, formulas, chemical systems, prototypes, and structural similarity
are audited across partitions. Exposure through a public foundation model is
reported separately from leakage within the fine-tuning experiment.

## Program structure

- [`phonon-environment-selection/`](phonon-environment-selection/) contains the
  completed supervised PBE study and its PBEsol transfer test.
- [`retrospective-bridge/`](retrospective-bridge/) reconstructs matched
  environment decisions across public atomistic studies.
- [`mlip-phonon-environment-selection/`](mlip-phonon-environment-selection/)
  contains the current universal-potential experiment, frozen protocols,
  measurements, outcomes, and support audit.

The current starting model, dataset versions, units, loss contract, candidate
memberships, target splits, and integrity hashes are defined inside the study
folders. Those records, rather than this overview, are the authoritative
experimental contracts.

## Scope and safety

The released studies cover phonons, dynamical stability, and related atomistic
prediction tasks. Catalysis, molecular dynamics, defects, and generative
materials design require their own qualified targets and evaluation contracts.
Prediction cannot replace reference calculations or uncertainty checks in
high-consequence scientific decisions.
