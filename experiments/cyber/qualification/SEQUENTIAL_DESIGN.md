# Prespecified sequential testing of raw reward variance

This independent-Bernoulli planning example shares the exact composite
null test in SIGNAL_DENSITY_COMPARISON.md. It is not a sequential
procedure for clustered task rollouts or general environment utility.

Choose L increasing fixed looks before observing outcomes and spend
alpha/L at each. At each look, reject only if the union-null p-value is
at most alpha/L. The probability of any rejection under every parameter
in the composite null is at most the sum of the marginal error bounds,
alpha. Correlation across looks does not invalidate this union bound.
No boundary calibrated at one baseline is reused elsewhere.
There is no early declaration of equality; no rejection at the final
look is not proof of equality.

The implementation checks cumulative counts and stops at the first
rejection. A separate finite-state evaluator propagates the four
possible independent Bernoulli outcome pairs each step, removes
rejected mass at scheduled looks and reports expected and maximum
per-arm trials. Evaluation is limited to at most 100 trials per arm;
the testing rule itself supports larger prespecified looks.

Illustration only, looks (20,40,60), alpha .05:

| p | q | Fixed power at 60 | Sequential rejection probability | Expected trials/arm |
| --- | --- | --- | --- | --- |
| .035 | .035 | .004933 | .001371 | 59.996 |
| .035 | .965 | .004933 | .001371 | 59.996 |
| .035 | .085 | .092482 | .053176 | 59.708 |
| .10 | .40 | .963881 | .924842 | 41.267 |
| .30 | .50 | .284384 | .153739 | 58.850 |

The tradeoff is explicit: under some alternatives early rejection
reduces average cost, while equal alpha spending can substantially
reduce power. The .035 rate is hypothetical pending a level-2 rerun.
These values are finite-state floating-point computations rather
than training experiments. Tests check both null branches across
the parameter grid, a one-look equivalence, probability mass and
valid cumulative inputs.

Run python -m unittest test_environment_ranking test_sequential_design.
