# Prospective PushT environment-selection panel

**Status:** complete, prospective decision record.

This experiment compares three ways to select 52 episodes from the same 206-
episode PushT pool:

- **Random:** uniform sampling without replacement.
- **Diversity-only:** greedy coverage selection without a quality gate.
- **Quality plus diversity:** the pinned Calibra quality filter followed by the
  same coverage stage.

The candidate memberships and the decision rule were frozen before candidate
training outcomes were opened. The frozen action was to abstain between the
diversity-only and quality-plus-diversity candidates; no ordering was asserted
between them.

## Matched contract

| Component | Frozen value |
| --- | --- |
| Dataset | `lerobot/pusht` at revision `7628202a2180972f291ba1bc6723834921e72c19` |
| Candidate budget | 52 episodes per arm |
| Policy | Diffusion policy |
| Optimization | 175,000 updates, batch size 64 |
| Image transform | Random 84 by 84 crop |
| Training seeds | 0, 1, 2 |
| Evaluation | 500 paired closed-loop episodes per arm and training seed |
| Primary endpoint | PushT closed-loop success percentage |
| Smallest effect of interest | 5 percentage points |
| Independent unit | Paired training seed |

The selection implementation and evaluation harness were pinned to Calibra
revision `5c60af73f3b86241c0b71b5d759c51dbde4fb616`.

## Results

| Candidate | Seed 0 | Seed 1 | Seed 2 | Mean | Regret |
| --- | ---: | ---: | ---: | ---: | ---: |
| Random | 21.8% | 27.2% | 25.6% | 24.87% | 3.87 pp |
| Diversity-only | 33.6% | 27.6% | 25.0% | **28.73%** | **0.00 pp** |
| Quality plus diversity | 27.4% | 24.4% | 26.2% | 26.00% | 2.73 pp |

The observed best candidate was diversity-only. It was inside the frozen
abstention set, so the abstention was correct. The quality-plus-diversity minus
diversity-only contrast was -2.73 percentage points, with a training-seed
95% interval from -11.98 to 6.51 percentage points.

The intervals are wide because there are only three independent training seeds.
The result supports safe abstention in this panel, not a general claim that one
selection method dominates another.

## Files

- [`data/outcomes.json`](data/outcomes.json): frozen protocol fields and the
  nine arm-by-seed outcomes.
- [`results/summary.json`](results/summary.json): deterministic derived result.
- [`scripts/reproduce.py`](scripts/reproduce.py): standard-library analysis.
- [`test_reproduce.py`](test_reproduce.py): integrity and chronology checks.
- [`SOURCES.json`](SOURCES.json): pinned upstream provenance and licenses.

## Interpretation

This panel answers a narrow question: under one PushT policy and one fixed
training/evaluation contract, did the pre-outcome action avoid excluding the
eventual best candidate? Yes.

It does not test physical hardware, new embodiments, new task families, or
simulation-to-reality transfer. It also does not show that a fitted predictor
beats the competent diversity baseline.
