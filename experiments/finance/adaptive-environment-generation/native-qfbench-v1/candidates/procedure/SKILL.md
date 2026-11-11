# Finance risk implementation checks v1

Use this procedure for quantitative-finance tasks that combine fitted risk
models, simulation, transition matrices, or cross-file reporting. It was
derived from two development failures: a likelihood and resampling convention
miss in a DCC-GARCH task, and an inconsistent transition total in a credit
migration task.

## Scope and removal

Apply the procedure only when the task contains at least one of these elements:
conditional likelihoods, reproducible resampling, cohort transition counts,
portfolio tail risk, or summaries repeated across output files. The task
instruction remains authoritative. Remove this resource after the task, and do
not carry task data, fitted values, or expected answers into another run.

## 1. Build a contract ledger

Before coding, list each reported quantity with its unit, sign, conditioning
set, source array, random-number contract, and rounding rule. Mark quantities
that appear in more than one output. Derive every repeated quantity once, then
serialize it into each required file. Add assertions for every identity that
crosses file boundaries.

## 2. Keep likelihood conventions explicit

For DCC correlation QML, distinguish the correlation contribution from the
full multivariate Gaussian likelihood. When standardized residuals are `z_t`
and conditional correlations are `R_t`, the correlation contribution is

`-0.5 * sum(logdet(R_t) + z_t' inv(R_t) z_t - z_t' z_t)`.

Use one function for both optimization and the reported value. If the task
requests another convention, state it and change both uses together. Check the
sign, the inclusion of the diagonal baseline, the initialization of `Q_0`, and
the alignment between residual row `t` and correlation matrix `R_t`.

## 3. Make stochastic simulation reproducible by construction

For a stationary bootstrap, resample whole multivariate residual rows. Draw a
uniform starting index. At each subsequent position, restart from a new uniform
index with probability `p`; otherwise advance the previous index by one with
circular wraparound. Freeze the RNG family, seed, draw order, restart rule,
sample size, and whether a sample is reused across dates. Validate the index
trace on a small deterministic example before using it for VaR or CVaR.

Keep the loss convention consistent. If returns are simulated, positive losses
are their negatives. VaR is a loss quantile, and CVaR is the mean loss in the
same tail. Assert that both are finite, CVaR is at least VaR, and Monte Carlo
results are unchanged under a repeated run with the same seed.

## 4. Use one count cube for migration outputs

After rating mapping, withdrawal censoring, and default correction, retain one
canonical count array with axes `(cohort, origin, destination)`. For each
non-default origin, cohort size is the sum over every destination, including
Default. Total transitions are the sum of those same cohort sizes. Do not add
the absorbing Default-origin row to the summary total.

Derive transition probabilities, default rates, cohort sizes, and summary
counts from this array. Before writing files, assert:

- every nonempty transition row sums to one;
- the Default row is absorbing when required;
- per-rating defaults sum to aggregate defaults;
- total transitions equal the sum of reported non-default cohort sizes;
- every cumulative default probability stays in `[0, 1]` and is nondecreasing
  with horizon.

## 5. Reconcile before finalizing

Reload every serialized output and recompute the cross-file identities from the
written values. Treat a mismatch as a failed task even if each file is locally
plausible. Preserve full precision until serialization, then apply only the
rounding requested by the task.
