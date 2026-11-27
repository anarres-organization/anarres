# Verifier reliability pilot

**Status:** Historical descriptive summary and prospective feasibility design.
The earlier training-effect and pooled-item power claims are withdrawn.
The released aggregate counts have not been reconstructed from raw run records.

## Historical observations

The recorded settings are Qwen3-0.6B with a low-rank adapter, 40 GRPO steps,
three prompts per step, six rollouts per prompt, 384 new tokens, learning rate
5e-5, KL coefficient .02, clip .2, temperature 1, top-p .95, and greedy
evaluation on the first 300 GSM8K test items. These are reported settings,
not verified immutable run provenance.

Each condition records one trained policy. Evaluation items are repeated
measurements of that policy, not independent training runs. The following
differences describe the particular reported policy pairs only; they cannot
isolate the training intervention from seed and other run-level variation.

| Comparison | Control | Treatment | Difference (pp) | Discordant counts | Conditional item p |
| --- | --- | --- | --- | --- | --- |
| Clean vs iid false negative | 50.7% | 47.3% | -3.33 | 52 / 42 | .3533 |
| Clean vs group false negative | 50.7% | 52.7% | +2.00 | 44 / 50 | .6063 |
| Clean vs no group baseline | 50.7% | 24.3% | -26.33 | 99 / 20 | 9.2025e-14 |
| Clean seed pair | 50.7% | 48.3% | -2.33 | 58 / 51 | .5657 |
| Open-style seed pair | 63.0% | 46.7% | -16.33 | 82 / 33 | 5.5714e-6 |

The final two rows record different seed pairs under their respective reported
configurations. They show why run-level variation must be measured, but two
pairs are insufficient for estimating the relevant variance. Neither their
maximum nor the item-level McNemar result is a threshold for attributing a
difference to the verifier. The sixth CSV row changes both style and seed and
is excluded from interpretation.

The McNemar calculations and the conditional item-resolution calculation
remain arithmetic diagnostics on the archived counts. Their assumptions
concern item outcomes within a realized pair. They do not estimate power
for a training intervention.

## Prospective design: nine matched independent seed pairs

The feasibility plan is frozen in [design/next-panel.json](design/next-panel.json).
For each of nine distinct training seeds, train a clean and a 38% iid
false-negative verifier policy from the same pinned initial configuration,
holding all other factors fixed. Evaluate both on one identical pinned
300-item panel. The experimental unit is the matched training seed pair, not
an evaluation item. Training requires 18 completed distinct runs.

For seed s, define d_s = 100 * (treatment_correct - control_correct) / 300.
The primary summary is the mean of the nine d_s values, their between-pair
standard deviation, and an approximate paired t interval (8 degrees of
freedom) assuming independent, approximately normal seed-level differences.
The sign test is secondary and addresses directional balance, not a mean
effect. A zero estimated variance is flagged by omitting the interval.
The design is feasibility-only, with no 80% power claim. A larger
confirmatory design requires independent seed-level variance calibration
and a new frozen protocol before observing its results.

The analysis takes one row per pair, rejects duplicate seeds and reused
training-run identities, requires the same evaluation panel digest, rejects
pooled-item rows, and will not accept a partial nine-pair design. It reports
a descriptive result and does not declare causal attribution. The seed and
run-ID checks are structural safeguards, not proof of independent execution.

## Provenance and release gates

[Historical provenance status](data/provenance.json) records the missing
immutable model/dataset revisions, code and configuration digests, training
and evaluation seed identifiers, checkpoint identifiers, perturbation seeds,
and item-level extraction artifacts. The original aggregate CSV is retained
without alteration. Its content hash establishes integrity of this file only,
not authenticity of the reported runs. It is not a verified training record
until those underlying artifacts are recovered and independently reconciled.

Before prospective execution, pin model/dataset revisions, panel membership
and SHA-256, code/configuration hashes, nine seed values, RNG and verifier
contracts, checkpoint paths, and item-level output extraction. Release the
18 run receipts and paired item-level counts. No prospective run has been
claimed or created here.

## Reproduction

From this directory:

    python scripts/recompute_exact_mcnemar.py
    python scripts/detectable_difference.py
    python scripts/resolution_plan.py
    python -m unittest discover -s scripts -p test_run_level_analysis.py

For completed prospective data only:

    python scripts/resolution_plan.py --runs <paired-run-csv>

The run CSV must contain seed, control_run_id, treatment_run_id, panel_sha256,
n_items, correct_control and correct_treatment. The analysis checks a
content-addressed protocol and manifest before accepting results.

## Scope

This record can establish arithmetic consistency of released aggregates and
a better prospective analysis design. It cannot establish a verified
training-effect estimate or a powered confirmatory trial without the
missing provenance and independent training repetitions.
