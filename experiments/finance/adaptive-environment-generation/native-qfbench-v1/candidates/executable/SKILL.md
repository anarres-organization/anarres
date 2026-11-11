# Finance risk invariant helpers v1

This optional resource provides small helpers for the failure modes observed in
the development tasks: DCC likelihood convention, reproducible stationary
resampling, transition-count reconciliation, and tail-risk sign consistency.
The task instruction remains authoritative. Copy only the functions that match
the task and remove the resource after the run.

```python
import numpy as np


def dcc_correlation_log_likelihood(z, correlations):
    """Correlation-only Gaussian DCC log likelihood.

    The diagonal standardized-residual contribution is subtracted so identity
    correlations have zero correlation contribution.
    """
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
    """Politis-Romano stationary-bootstrap indices with circular continuation."""
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
    """Return cohort-by-origin sizes from one canonical transition count cube."""
    counts = np.asarray(counts)
    if counts.ndim != 3 or counts.shape[1] != counts.shape[2]:
        raise ValueError("counts must have shape (cohort, origin, destination)")
    if not 0 < n_nondefault < counts.shape[1]:
        raise ValueError("n_nondefault must exclude at least one absorbing state")
    if np.any(counts < 0):
        raise ValueError("transition counts cannot be negative")
    return counts[:, :n_nondefault, :].sum(axis=2)


def reconcile_transition_total(summary_total, cohort_sizes, tolerance=0):
    """Require the summary and reported non-default cohort sizes to agree."""
    reported = int(np.asarray(cohort_sizes).sum())
    if abs(int(summary_total) - reported) > tolerance:
        raise ValueError(
            f"transition total mismatch: summary={summary_total}, cohorts={reported}"
        )
    return reported


def empirical_var_cvar(losses, confidence):
    """Return positive-loss empirical VaR and CVaR under one tail convention."""
    losses = np.asarray(losses, dtype=float)
    if losses.ndim != 1 or not np.isfinite(losses).all():
        raise ValueError("losses must be a finite one-dimensional array")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    var = float(np.quantile(losses, confidence))
    tail = losses[losses >= var]
    cvar = float(tail.mean())
    if cvar < var:
        raise AssertionError("CVaR must be at least VaR")
    return var, cvar
```

Before using a helper, test its identities on a small synthetic case. For DCC,
identity correlation matrices must produce a zero correlation contribution.
For transition counts, the summary total must equal the sum of non-default
origin cohort sizes. For resampling, repeated calls with the same seed must
return identical in-range indices.
