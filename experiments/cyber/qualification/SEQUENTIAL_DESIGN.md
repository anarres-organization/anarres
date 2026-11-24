# Stopping early without changing the answer

The comparison note fixes 400 rollouts per arm and looks once. That is honest but
expensive, and a screening programme pays the full price on every candidate that
turns out to be no different. A group-sequential variant looks at 160, 320, and
480 trials per arm, rejects when the profile likelihood ratio crosses a boundary,
and accepts when the ratio falls below one, which is the point where the data
favour equal density.

Error rates and expected sample sizes come from an exact dynamic program over the
joint lattice of successes. Nothing is simulated.

## The boundary

At looks 160, 320, and 480 with a constant rejection boundary and futility at a
ratio below one after the first look, bisection on the exact null gives a
boundary of 5.394 and a size of 0.0494.

## Results

| density ratio | fixed power at 400 | sequential power | sequential trials | saving |
| --- | --- | --- | --- | --- |
| 2.3 | 0.864 | 0.861 | 310 | 23% |
| 1.8 | 0.512 | 0.483 | 372 | 7% |
| 1.5 | 0.255 | 0.228 | 378 | 5% |

Under the null the design costs 363 trials against 400, so it is cheaper there
too. At the ratio the fixed protocol is built to detect, power is unchanged while
the budget falls by nearly a quarter.

## How to read it

- Use the sequential design when a real difference is plausible, which is the
  screening case. It matches the fixed protocol's power at the declared
  minimum detectable ratio and saves about a fifth of the rollouts.
- Before that ratio the design trades a few points of power for very little
  saving. If the interesting effects are below detectability, spend the budget on
  a larger nominal design rather than on early stopping.
- Futility must not run at the first look. With 160 trials on a 0.035 baseline,
  most null trajectories have not yet separated, and stopping them there costs
  nine points of power.

## A side result

The profile likelihood ratio for equal density has a closed form. The null splits
into equal rates and into rates summing to one, and each branch maximises at a
rational point, so the statistic is a difference of log likelihoods with no
numerical search. `test_sequential_design.py` checks the closed form against the
profiled optimiser on sample points and finds agreement to six places, which also
means the whole lattice can be evaluated at once.

## Limits

- The counts are discrete and sparse, so the boundary is conservative at 0.0494
  rather than exactly nominal.
- The table covers one baseline. At denser baselines the same boundary holds less
  well, because the null trajectory separates earlier and the futility rule bites
  sooner.
