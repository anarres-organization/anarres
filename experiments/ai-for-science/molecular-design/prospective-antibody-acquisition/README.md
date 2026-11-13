# Prospective antibody-acquisition panel

## Question

Can a simple acquisition rule learned from earlier molecular and protein
studies choose useful experiments on independently assembled antibody-binding
landscapes? This study freezes one answer before evaluating the candidate
panel: use upper-confidence-bound acquisition with equal weight on predicted
affinity and model uncertainty.

The panel contains six AbBiBench antibody--antigen assays that were not used to
choose the rule. Each assay compares five acquisition strategies under the same
initial observations, batch sizes, surrogate, label budget, and random seeds.
The primary outcome is finite-budget recovery of the assay's top 2% of variants.

## Chronology

1. Pin the official AbBiBench revision and six source-file hashes.
2. Freeze the candidate assays, acquisition rules, model, seeds, budgets,
   prediction, and scoring contract.
3. Run the complete assay--strategy--seed matrix without inspecting partial
   comparative outcomes.
4. Verify every unit and source identity.
5. Open and score results only after the complete-matrix gate passes.

The study is complete. `FROZEN_CONTRACT.json` is the authoritative protocol,
and `FREEZE.json` binds that protocol to the executable runner and scorer.
`RELEASE_GATE.json` records the complete 150-unit matrix, while
`OUTCOME_CURVES.json` and `RESULTS.json` contain the released trajectories and
aggregate score.

## Result

The frozen UCB prediction is best on three of six assays and earns 83.3%
pairwise credit against the four alternatives. Its mean normalized allocation
regret is 0.241. UCB exceeds random acquisition on every assay and has the
highest mean raw curve utility across the panel.

Greedy acquisition is best on the other three assays and reaches lower mean
normalized regret, 0.125. The result supports UCB as a competitive transfer
rule without establishing a unique advantage over greedy acquisition. The next
decision problem is therefore to predict when exploration adds value beyond a
strong exploitation baseline.

## Run the sealed matrix

Install the experiment-local dependencies without adding them to the native
Anarres CLI:

```bash
uv sync --project experiments/ai-for-science/molecular-design/prospective-antibody-acquisition
```

Download the six files listed in `SOURCES.json` into one source directory.
Run one unit per assay, strategy, and seed:

```bash
uv run --project experiments/ai-for-science/molecular-design/prospective-antibody-acquisition \
  python experiments/ai-for-science/molecular-design/prospective-antibody-acquisition/scripts/run_unit.py \
  --source-dir /path/to/abbibench \
  --output-dir /path/to/sealed-units \
  --assay 1mlc --strategy ucb --seed 7
```

After all 150 units exist, apply the completeness gate and then score:

```bash
uv run --project experiments/ai-for-science/molecular-design/prospective-antibody-acquisition \
  python experiments/ai-for-science/molecular-design/prospective-antibody-acquisition/scripts/gate_complete_panel.py \
  --source-dir /path/to/abbibench \
  --unit-dir /path/to/sealed-units \
  --output /path/to/RELEASE_GATE.json

uv run --project experiments/ai-for-science/molecular-design/prospective-antibody-acquisition \
  python experiments/ai-for-science/molecular-design/prospective-antibody-acquisition/scripts/score_panel.py \
  --unit-dir /path/to/sealed-units \
  --release-gate /path/to/RELEASE_GATE.json \
  --output /path/to/RESULTS.json
```

This is a retrospective simulation on public experimental measurements. Its
prospective status concerns the frozen candidate panel, prediction, and analysis
chronology. It does not provide prospective wet-lab evidence.

