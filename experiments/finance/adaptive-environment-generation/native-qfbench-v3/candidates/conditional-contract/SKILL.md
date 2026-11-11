# Conditional risk and backtest timing contract v3

Use this resource for quantitative-finance tasks that join fitted risk models,
portfolio simulation, or rolling backtests. The assignment remains
authoritative. Record any ambiguity, prefer its literal convention, and do not
add timing or sampling rules that the assignment does not request.

## Conditional and unconditional variance

For a fitted GARCH(1,1), keep three quantities separate:

- filtered variance `h_t` attached to each observed return;
- the one-step forecast `h_next = omega + alpha * epsilon_last**2 + beta * h_last`;
- long-run variance `omega / (1 - alpha - beta)` when `alpha + beta < 1`.

Long-run variance describes an unconditional level. A valuation or forward
risk calculation at the end of the sample should use the one-step conditional
forecast unless the assignment explicitly requests the long-run level. Report
long-run variance separately when it is an output. Keep optimization units,
reported units, and annualization explicit.

For DCC or another conditional covariance model, use the same recursion for
optimization, reporting, and portfolio aggregation. Check symmetry, positive
definiteness, unit-diagonal correlations, and `portfolio_variance = w' H w`.

## Analytical barrier valuation

Match the formula to the barrier and strike ordering, rebate, carry, and
monitoring convention. For a continuously monitored down-and-out call with
zero rebate and barrier below the strike, check the analytical value against
an independently integrated killed transition density. Validate delta by a
centered spot bump. Keep the number of options, unit option value, total option
value, and note delta linked by exact identities.

When a structured note combines a discounted principal claim with option
participation, compute each component once. Use the one-step conditional
volatility consistently for option value, delta, breakeven volatility, and
delta-based risk. Recompute `fair_value = bond_pv + option_value` from the
serialized outputs.

## Rolling signals and rebalance timing

Clean the feed before truncating to the most recent requested number of valid
observations. A rolling window of length `W` first produces a signal on the
`W`th retained observation. If the assignment requests monthly rebalancing,
use the final available observation in every calendar period represented in
the retained data, including the terminal period unless it is explicitly
excluded.

Create the initial allocation at the first eligible signal. Apply each signal
or allocation with the lag required to prevent look-ahead, then hold it until
the next rebalance. If weights are scaled below one, leave the residual in cash
at the stated cash return. Before computing performance, assert the expected
counts for signals, rebalances, implemented returns, and trailing risk windows.

## Tail risk and credit simulation

Use one loss convention throughout. VaR is a positive loss quantile and CVaR
or ES is the mean loss in the same tail. Check `CVaR >= VaR >= 0` and retain
full precision until serialization.

For portfolio credit risk, separate marginal transition or default behavior,
dependence generation, exposure or recovery mapping, and portfolio
aggregation. Freeze the random-number generator, seed, draw order, scenario
count, and array axes. Reuse one canonical scenario-loss array for portfolio
VaR, CVaR, concentrations, and marginal contributions. Reconcile every
reported total to that array.

## Final checks

Reload every required output and verify schemas, row counts, date alignment,
probability bounds, timing counts, covariance identities, component sums, and
rounding. Remove this resource after the run. It contains no task data, fitted
value, expected answer, or verifier output and must not carry task state into a
later workspace.
