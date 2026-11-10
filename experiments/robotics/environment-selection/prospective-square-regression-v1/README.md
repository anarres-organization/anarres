# Prospective environment and regression prediction on RoboMimic Square

**Status:** measurement protocol frozen; candidate-policy outcomes unopened.

This study asks whether measurements from a reference robot policy can select
a useful demonstration environment and identify where a trained policy may
regress. It uses the official 300-demonstration RoboMimic Square multi-human
v1.4.1 dataset and the Diffusion Policy contract released with CuraEval.

The experiment first creates a fixed bank of 128 simulator initial states. Three
all-data probe policies estimate which states remain difficult. Those outcomes
are measurement inputs, not candidate-policy outcomes. Candidate construction
then combines the measured failure map with geometric coverage of the same
initial-state distribution. Every unopened candidate is trained from scratch for
the same number of optimizer steps and evaluated on the identical state bank.

## Candidate panel

The panel contains random and shortest-trajectory baselines, an unweighted
coverage subset, a failure-weighted coverage subset, and a failure-weighted
coverage subset restricted to relatively short demonstrations. Coverage
selection retains 50 demonstrations from each of the better, okay, and worse
operator tiers. The all-data probe policies provide a reference surface but are
not presented as unopened candidate outcomes.

The frozen point prediction selects `failure_coverage_short_50`. The aggregate
test measures its success rate and allocation regret. The regression test asks
whether the product of starting-policy failure probability and candidate
coverage distance predicts candidate-minus-reference changes across eight
predefined initial-state strata.

## Why this test is separate from the Can release

The completed Can comparison has success rates between 93.8% and 98.8%. Its
frozen choice beats random selection but does not beat the shortest subset.
Square provides a less saturated setting and a new outcome: paired performance
on fixed initial states rather than aggregate success alone. The protocol also
reports the cost of training and evaluating the probe policies instead of
treating measurement as free.

[`PROTOCOL.json`](PROTOCOL.json) fixes the chronology, candidates, prediction,
training budget, state-bank construction, and scoring rules. [`SOURCES.json`](SOURCES.json)
records the source revisions and dataset identity. [`FREEZE.json`](FREEZE.json)
binds both records to the released fixed-state bank. Scripts in this directory
materialize the state bank and candidate memberships without opening candidate
outcomes.

Verify the outcome-blind freeze with:

```bash
python scripts/verify_freeze.py
python -m unittest test_freeze.py
```

## Scope

This is one simulated manipulation task, one policy family, and one fixed
training budget. The initial-state representation uses square-nut pose and is
specific to this simulator contract. A successful result would support
prospective environment and regression prediction within this setting. It would
not establish a general robotics allocator.
