# Verifier reliability pilot

**Status:** Exploratory pilot. Every comparison below is retrospective on one released panel, with one starting policy, one training budget, and one seed per cell.

## Overview

Verifier noise is a candidate environment factor: a reward function that mis-scores correct answers changes the learning signal without changing the prompts. This pilot asks how much a large false-negative rate moves a held-out outcome when the trainer is otherwise identical, and whether the answer depends on how the false negatives are distributed across a prompt's rollouts.

The question:

> At a fixed small budget, does a 38% false-negative rate change held-out pass@1, and does grouped erasure of a prompt's signal differ from independent per-rollout flips?

A second question follows from the first. If per-item outcomes are unstable across seeds at this budget, small measured differences cannot be attributed to any single intervention. The record therefore includes two seed pairs measured under identical configurations.

## Design

Starting policy: Qwen3-0.6B with a low-rank adapter. Trainer: group relative policy optimization with a group-mean baseline, 40 steps, 3 prompts per step, 6 rollouts per prompt, 384 new tokens per rollout, learning rate 5e-5, KL coefficient 0.02, clip 0.2, temperature 1.0, top-p 0.95. Training prompts come from the GSM8K training split. Evaluate with greedy decoding on the first 300 items of the GSM8K test split, one evaluation per trained checkpoint.

| Cell | Verifier | Baseline | Reading |
| --- | --- | --- | --- |
| clean | exact match, 0% false negative | group mean | Control |
| iid false negative | 38% of correct rollouts re-scored as incorrect, drawn independently per rollout | group mean | Noise without group structure |
| group false negative | 38% of prompts have every rollout re-scored as incorrect | group mean | Noise that erases a prompt's group signal |
| no group baseline | exact match | raw reward | Removes the group-mean baseline |

The independent unit is the held-out item. Each cell is scored on the same 300 items, so item-level pairing is exact and the discordant-pair counts are the released input.

## Result

| Comparison | Control | Treatment | Difference | Discordant pairs | Exact p |
| --- | --- | --- | --- | --- | --- |
| clean vs iid false negative | 50.7% | 47.3% | -3.3 points | 52 / 42 | 0.353 |
| clean vs group false negative | 50.7% | 52.7% | +2.0 points | 44 / 50 | 0.606 |
| clean vs no group baseline | 50.7% | 24.3% | -26.4 points | 99 / 20 | 9.2e-14 |

The untrained policy scores 41.3% on the same panel and decoding settings. The no-baseline cell lands 17.0 points below that score.

## Stability

Two pairs were trained under identical configurations with a different seed.

| Pair | Control | Treatment | Difference | Discordant pairs | Exact p |
| --- | --- | --- | --- | --- | --- |
| clean, seed 0 vs seed 1 | 50.7% | 48.3% | -2.3 points | 58 / 51 | 0.566 |
| open prompt style, seed 0 vs seed 1 | 63.0% | 46.7% | -16.3 points | 82 / 33 | 5.6e-06 |

The second pair flips 115 of 300 items, which exceeds the discordant counts of every verifier intervention in this record. Prompts are rendered in the open style for that pair, so its levels are comparable within the pair and not across tables.

## Resolution

A non-significant test does not establish a zero effect. This section states what each pair could have detected, so the negative rows stay bounded.

For a pair with discordant total `m` and `n` scored items, an alternative that moves outcomes by `d` points puts the expected count of control-only flips at `(m + d·n)/2`, so the count follows `Binomial(m, 0.5 + d·n/(2m))`. The rejection rule is the same two-sided exact binomial test used above. Power is the exact sum over that law, with no normal approximation and no simulation.

| Pair | Discordant | Observed difference | Smallest detectable difference at 80% power |
| --- | --- | --- | --- |
| clean vs iid false negative | 94 | -3.3 points | 9.0 points (13.5 flips) |
| clean vs group false negative | 94 | +2.0 points | 9.0 points (13.5 flips) |
| clean vs no group baseline | 119 | -26.4 points | 10.5 points (15.8 flips) |
| clean, seed 0 vs seed 1 | 109 | -2.3 points | 10.3 points (15.4 flips) |
| open prompt style, seed 0 vs seed 1 | 115 | -16.3 points | 10.3 points (15.4 flips) |

Read from this table, the two false-negative rows establish that a change below roughly 9 points is invisible at this design, and the no-baseline row exceeds its own resolution by a factor of 2.5. The seed pair in the open style also exceeds its resolution, which is why its gap is not attributable to the reward change alone.

## What the pilot supports

A 38% false-negative rate applied independently to rollouts moved held-out pass@1 by 3.3 points, below the 9.0 point resolution of that pair. Erasing the group signal for 38% of prompts moved the outcome by 2.0 points, also below resolution. Both interventions sit inside the spread produced by seed choice alone.

Removing the group-mean baseline moved the outcome by 26.4 points against a 10.5 point resolution, and placed the policy below its untrained score. At this budget the baseline term carries more of the training signal than the verifier's false-negative rate.

## What the pilot does not support

One pair in the released counts, `open_vs_unfinished_penalty`, returns a p-value of 0.033 for a 6.7 point gap, below its own resolution. Its two cells differ in prompt style and in seed, so the pair measures an intervention plus seed noise. The column `excluded_from_claims` marks that row and the README makes no claim from it. A 16.3 point seed gap on the same style shows that the 6.7 point gap is not attributable to the reward change.

No claim here extends to larger policies, longer budgets, other datasets, or other verifier error profiles. False-negative tolerance likely depends on policy breadth, which this pilot holds fixed at one model size.

## Experimental record

| Component | Released setting |
| --- | --- |
| Input | `data/paired_counts.csv`, one row per compared pair |
| Columns | correct counts for each cell, both-correct count, control-only and treatment-only counts, item count, exact p-value, claim exclusion flag |
| Rows | 6 pairs over the first 300 GSM8K test items |
| Primary outcome | pass@1 under greedy decoding |
| Integrity | `MANIFEST.sha256`, content hashes for the complete record |

The released record stores discordant counts rather than generations. The counts decompose into per-cell correct totals, so a reader can rebuild the reported accuracies and tests without hosting model outputs.

## Inspect the pilot

```bash
cd experiments/mathematics/verifier-reliability-pilot
python scripts/recompute_exact_mcnemar.py
python scripts/detectable_difference.py
python scripts/resolution_plan.py
```

The first command checks that each row's counts decompose into its two cell totals, then recomputes the two-sided exact McNemar p-value from the discordant counts and fails when a stored value disagrees by more than 5e-5. The second command computes the resolution table above from the same counts. Both are registered with `make study-check` as the studies "verifier reliability pilot counts" and "verifier reliability pilot resolution", so the released record is covered by the same gate as the rest of the repository.

The third command solves the inverse problem, the design that resolves a given effect, verifies the frozen design in `design/next-panel.json` against the released rate, and prints a verdict per released pair. It is registered as the study "verifier reliability pilot resolution plan".

## Design budget

`detectable_difference.py` fixes what each released pair could see. `scripts/resolution_plan.py` solves the inverse: for an effect of a given size, the number of held-out items and the number of seed-paired 300-item panels that reach 80% power at the same exact test. The discordant rate comes from the released counts, pooled over the five claim rows at 0.354, so the plan is tied to this panel's verifier and policy rather than to an assumed noise level.

| Effect | Items needed | Seed-paired 300-item panels | Discordant count at that size |
| --- | --- | --- | --- |
| 2.00 points | 6,991 | 24 | 2,475 |
| 3.30 points | 2,601 | 9 | 921 |
| 5.00 points | 1,138 | 4 | 403 |
| 9.00 points | 352 | 2 | 125 |

The 9.00 point row checks the solver against the released table: all five claim rows solve to 9.00, 9.00, 10.50, 10.25 and 10.25 points at n = 300, identical to the resolution table above, and the script fails when a solved value drifts by more than one 0.25 point search step.

Read the other way, the same arithmetic prices the negative rows. Resolution against the number of panels at this size:

| Panels | Items | Resolution at 80% power | Discordant at that size |
| --- | --- | --- | --- |
| 1 | 300 | 10.00 points | 106 |
| 2 | 600 | 7.00 points | 212 |
| 4 | 1,200 | 5.00 points | 425 |
| 8 | 2,400 | 3.50 points | 850 |

Eight panels of this size still resolve only 3.5 points, which is why a 3.3 point claim needs the ninth. The script also re-derives its rejection region straight from the test definition and fails when the two disagree past 1e-9, so the power numbers stay tied to the test the record actually uses.

Two consequences follow for a later comparison in this domain. A 3.3 point verifier effect needs about 2,600 items, which is nine seed-paired panels at this size, and a 2 point effect needs about 7,000. The seed pairs also set a floor: the largest recorded same-configuration shift is 16.33 points, above the resolution of every pair in this record, so a single-seed difference has to clear both bars before it counts as an effect.

The script prints a verdict per intervention row using that rule. A verifier difference counts when it exceeds the pair's resolution and the recorded seed spread. Both false-negative rows stay unresolved at -3.33 and +2.00 points, and the baseline row clears both bars at -26.33 points.

## Frozen next-panel design

`design/next-panel.json` fixes the design that would resolve the iid false-negative effect, and the solver verifies it on every run rather than the reader trusting the table. The run fails when the frozen numbers stop matching the released discordant rate.

| Field | Frozen value |
| --- | --- |
| Target effect | 3.30 points |
| Panels | 9 of 300 items |
| Items per arm | 2,700 |
| Required by the solver | 2,601 |
| Resolution at that size | 3.25 points |
| Training runs | 18 (9 intervention, 9 same-seed control) |
| Primary test | two-sided exact McNemar, pooled over the nine panels |

Pairing is the reason the frozen design clears the 3.3 point target that the single-pair budget just misses. Each intervention panel is trained and scored beside a clean panel at the same seed, so the contrast is within-pair and seed spread enters both arms instead of being charged to one of them. The 16.33 point band in this record comes from unpaired cross-seed comparisons and is not the floor that a paired contrast has to clear.

Nine panels is the first budget that reaches the target: eight resolve 3.50 points, nine resolve 3.25.

## Scope

One policy family at one scale, one deterministic verifier, one reward contract, one dataset, one 40-step budget, and one seed per cell apart from the two stability pairs. The evidence is exploratory. Treating the 38% rate as harmless under a wider budget or a larger policy requires a prospective run with the budget fixed in advance.
