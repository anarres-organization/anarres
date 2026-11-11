# Finance risk contract and invariant toolkit v1

Use this resource for quantitative-finance tasks that combine fitted risk
models, simulation, transition matrices, or cross-file reporting. It addresses
three development failure types: a DCC likelihood convention mismatch, a
stationary-bootstrap reproducibility mismatch, and a credit-transition total
computed from a broader origin set than the reported cohort sizes.

The task instruction remains authoritative. Apply only sections that match the
task, remove this resource after the run, and never carry fitted values or
expected answers between tasks.

## Procedure

Create a contract ledger before coding. For every reported quantity, record its
unit, sign, conditioning set, source array, RNG contract, and rounding rule.
Compute values that appear in multiple outputs once and serialize the same
value everywhere.

For DCC correlation QML, keep the correlation contribution separate from the
full multivariate likelihood. With standardized residuals `z_t` and
correlations `R_t`, use
`-0.5 * sum(logdet(R_t) + z_t' inv(R_t) z_t - z_t' z_t)` when the task requests
the correlation contribution. Optimization and reporting must call the same
function.

For stationary bootstrap simulation, resample complete residual rows. Freeze
the RNG family, seed, restart probability, draw order, circular continuation,
sample size, and sample-reuse policy. Check the generated index trace on a
small deterministic example.

For migration analysis, retain one canonical count cube after mapping,
withdrawal censoring, and default correction. Cohort sizes and total
transitions must both sum over non-default origins and all destinations. The
absorbing Default-origin row does not enter that total. Reload serialized
outputs and check every cross-file identity before finishing.

## Tested helpers

```python
import numpy as np


def dcc_correlation_log_likelihood(z, correlations):
    z = np.asarray(z, dtype=float)
    correlations = np.asarray(correlations, dtype=float)
    if correlations.shape != (len(z), z.shape[1], z.shape[1]):
        raise ValueError("correlations must have shape (time, assets, assets)")
    total = 0.0
    for row, corr in zip(z, correlations, strict=True):
        sign, logdet = np.linalg.slogdet(corr)
        if sign <= 0:
            raise ValueError("correlation matrix is not positive definite")
        total += logdet + row @ np.linalg.solve(corr, row) - row @ row
    return -0.5 * float(total)


def stationary_bootstrap_indices(n_observations, sample_size, restart_probability, seed):
    if n_observations <= 0 or sample_size <= 0:
        raise ValueError("observation and sample counts must be positive")
    if not 0 < restart_probability <= 1:
        raise ValueError("restart_probability must lie in (0, 1]")
    rng = np.random.default_rng(seed)
    indices = np.empty(sample_size, dtype=int)
    indices[0] = rng.integers(n_observations)
    for position in range(1, sample_size):
        if rng.random() < restart_probability:
            indices[position] = rng.integers(n_observations)
        else:
            indices[position] = (indices[position - 1] + 1) % n_observations
    return indices


def nondefault_cohort_sizes(counts, n_nondefault):
    counts = np.asarray(counts)
    if counts.ndim != 3 or counts.shape[1] != counts.shape[2]:
        raise ValueError("counts must have shape (cohort, origin, destination)")
    if not 0 < n_nondefault < counts.shape[1] or np.any(counts < 0):
        raise ValueError("invalid non-default count cube")
    return counts[:, :n_nondefault, :].sum(axis=2)


def reconcile_transition_total(summary_total, cohort_sizes, tolerance=0):
    reported = int(np.asarray(cohort_sizes).sum())
    if abs(int(summary_total) - reported) > tolerance:
        raise ValueError(
            f"transition total mismatch: summary={summary_total}, cohorts={reported}"
        )
    return reported


def empirical_var_cvar(losses, confidence):
    losses = np.asarray(losses, dtype=float)
    if losses.ndim != 1 or not np.isfinite(losses).all():
        raise ValueError("losses must be a finite one-dimensional array")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    var = float(np.quantile(losses, confidence))
    cvar = float(losses[losses >= var].mean())
    if cvar < var:
        raise AssertionError("CVaR must be at least VaR")
    return var, cvar
```

Test each used helper on a small synthetic case. Identity DCC correlations must
have zero correlation contribution. Repeated bootstrap calls with the same
seed must match. Transition summaries must reconcile exactly. CVaR must be at
least VaR under the same positive-loss convention.
