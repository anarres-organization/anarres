# Quantitative risk contract toolkit v2

Use this resource for quantitative-finance tasks that combine fitted models,
simulation, tail-risk estimates, portfolio aggregation, or repeated reports.
The task instruction remains authoritative. Apply only the relevant sections,
and remove this resource after the task.

## Establish the numerical contract

Before implementation, record each requested quantity's unit, sign,
conditioning set, source array, random-number contract, and rounding rule.
Record every identity repeated across output files. Compute repeated quantities
once and serialize them consistently.

Keep returns and losses distinct. When losses are positive, VaR is a positive
loss quantile and CVaR or ES is the mean loss in the same tail. For every
reported tail measure, verify finiteness, sign, ordering, and the requested
confidence convention. Preserve full precision until serialization.

## Fit conditional risk models consistently

Use the same recursion and likelihood convention for optimization, reporting,
and downstream covariance construction. In DCC correlation QML, the
correlation contribution for standardized residuals `z_t` and correlations
`R_t` is

`-0.5 * sum(logdet(R_t) + z_t' solve(R_t, z_t) - z_t' z_t)`.

Check initialization, row alignment, parameter constraints, covariance
symmetry, positive definiteness, and unit-diagonal correlations. Portfolio
variance must reconcile with `w' H_t w` after every covariance transformation.

## Make simulation contracts executable

Treat the random-number generator, seed, draw order, path shape, restart rule,
and sample-reuse policy as part of the result. For stationary bootstrap
indices, sample a starting observation, restart from a uniform observation with
probability `p`, and otherwise continue circularly. Resample complete
multivariate rows. Run the generator twice with the same seed and require an
identical index tensor before computing any risk measure.

For Monte Carlo portfolio risk, validate marginal distributions, dependence,
portfolio aggregation, and loss conversion separately. Compare the final
sample count and array axes with the instruction before taking quantiles.

## Reconcile cohort and portfolio outputs

Use one canonical intermediate representation for every repeated report. For
credit transitions, retain one `(cohort, origin, destination)` count cube after
mapping and censoring. Cohort sizes and total transitions must use the same
non-default origins and all destinations. The absorbing Default-origin row does
not enter a non-default cohort total.

For portfolio decompositions, verify that component contributions sum to the
reported portfolio total within the requested tolerance. For regime or
scenario summaries, recompute weighted totals from the serialized rows rather
than from an independent code path.

## Final validation

Reload every output and assert the requested schemas, row counts, date
alignment, probability bounds, covariance identities, cross-file totals, and
rounding conventions. A locally plausible file is insufficient when the
outputs disagree with one another.

### Reusable invariants

```python
import numpy as np


def empirical_var_cvar(losses, confidence):
    losses = np.asarray(losses, dtype=float)
    if losses.ndim != 1 or not np.isfinite(losses).all():
        raise ValueError("losses must be finite and one-dimensional")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    var = float(np.quantile(losses, confidence))
    cvar = float(losses[losses >= var].mean())
    if cvar < var:
        raise AssertionError("CVaR must be at least VaR")
    return var, cvar


def reconcile_portfolio_variance(weights, covariance, reported, atol=1e-10):
    weights = np.asarray(weights, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    expected = float(weights @ covariance @ weights)
    if not np.isclose(expected, reported, atol=atol, rtol=0):
        raise ValueError(f"portfolio variance mismatch: {reported} != {expected}")
    return expected


def reconcile_transition_total(summary_total, count_cube, n_nondefault):
    counts = np.asarray(count_cube)
    if counts.ndim != 3 or counts.shape[1] != counts.shape[2]:
        raise ValueError("counts must have cohort, origin, destination axes")
    expected = int(counts[:, :n_nondefault, :].sum())
    if int(summary_total) != expected:
        raise ValueError(f"transition total mismatch: {summary_total} != {expected}")
    return expected
```

## Scope and removal

This resource is version 2 and is scoped to numerical risk workflows involving
conditional covariance, simulation, VaR/CVaR/ES, transition counts, or
cross-file reconciliation. It contains no task data, fitted value, expected
answer, or verifier output. Remove it after the run and do not transfer task
state between workspaces.
