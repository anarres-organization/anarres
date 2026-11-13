# Prospective protein-acquisition panel

## Question

Does greedy acquisition provide a reliable default for finite-budget protein
optimization beyond the antibody landscapes used to choose it? This study
freezes greedy acquisition as its point prediction before evaluating seven new
FLIP2 protein datasets.

The candidate panel spans enzymes, protein interactions, stability, and
light-sensitive proteins. Each dataset compares greedy, UCB, Thompson,
uncertainty-only, and random acquisition under a shared representation,
surrogate, label budget, and seed set. Large datasets are capped at 5,000
variants by an outcome-blind sequence hash before any target value is read.

## Why greedy is frozen

Two earlier results motivate the prediction. In the independent AbBiBench
panel, greedy acquisition has lower normalized regret than UCB. Greenman et al.
also report that UCB and Thompson sampling usually improve over random
acquisition but do not outperform greedy acquisition across the AAV, GB1, and
Meltome protein landscapes. FLIP2 supplies seven new datasets that are separate
from both sources.

## Chronology

1. Pin the official FLIP2 revision and seven split-file hashes.
2. Freeze the datasets, deterministic caps, candidates, model, budgets, seeds,
   greedy prediction, and scoring contract.
3. Run the complete dataset--strategy--seed matrix without inspecting partial
   comparative outcomes.
4. Verify every unit and source identity.
5. Open and score outcomes only after the complete-matrix gate passes.

The study is currently frozen and unscored. `FROZEN_CONTRACT.json` defines the
protocol, while `FREEZE.json` binds it to the executable runner and scorer.

This is a retrospectively executable simulation on public experimental data.
Its prospective status concerns the frozen candidate panel, prediction, and
analysis chronology. It does not provide prospective wet-lab evidence.

