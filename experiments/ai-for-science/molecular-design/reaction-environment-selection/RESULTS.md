# Prospective molecular environment result

The first matched RxnFlow decision is complete. The operational hybrid and
graph-aware hybrid were constructed from frozen starting-policy measurements,
trained from the same Q07820 warm start under the same replay and optimizer
contract, and evaluated only after the complete two-seed endpoint matrix passed
its integrity gate.

The frozen graph-aware forecast ranked the operational hybrid above the
graph-aware hybrid at all three budgets. That ordering was correct at 12,800,
25,600, and 40,000 target-oracle attempts, giving zero point-prediction regret.
The observed advantages were 0.122, 0.085, and 0.208 percentage points of
unique qualifying-hit rate. Both seeds agreed on the winner at the first and
third budgets, while they disagreed at the middle budget.

| Target-oracle attempts | Frozen point winner | Observed winner | Observed margin | Seed agreement | Frozen action |
| ---: | --- | --- | ---: | --- | --- |
| 12,800 | Operational hybrid | Operational hybrid | 0.122 pp | Yes | Abstain |
| 25,600 | Operational hybrid | Operational hybrid | 0.085 pp | No | Abstain |
| 40,000 | Operational hybrid | Operational hybrid | 0.208 pp | Yes | Abstain |

The point forecast and the decision rule answer different questions. The
forecast records the higher predicted utility. The decision rule issues that
choice only when its predicted margin exceeds the largest leave-one-development-
bank residual. The predicted margin was 0.035 percentage points, while the
prespecified uncertainty half-width was 1.198 points. The rule therefore
abstained at every budget. This result supports directional transfer of the
graph-aware representation, but it does not establish a reliable allocation
advantage between these two near-tied banks.

The graph-aware model achieved 0.433-point curve RMSE and the correct pairwise
ordering at all three budgets. The operational model achieved slightly lower
curve RMSE, 0.383 points, but reversed the pair at every budget. Curve calibration
and decision ordering therefore remain distinct evaluation targets.

## Integrity record

The prospective chronology is preserved by four compact artifacts:

- [`PROSPECTIVE_FREEZE_V1.json`](PROSPECTIVE_FREEZE_V1.json) records the
  forecasts, candidate memberships, model coefficients, uncertainty rule, and
  unopened-outcome state.
- [`PROSPECTIVE_TRAINING_GATE.json`](PROSPECTIVE_TRAINING_GATE.json) verifies
  four training trajectories and twelve frozen checkpoints before endpoint
  outcomes are opened.
- [`PROSPECTIVE_ENDPOINT_GATE.json`](PROSPECTIVE_ENDPOINT_GATE.json) verifies
  the two warm starts and twelve trained-policy panels, their policy and sample
  identities, and the split-union docking and metric artifacts.
- [`PROSPECTIVE_RESULTS.json`](PROSPECTIVE_RESULTS.json) contains the released
  seed-level utilities and scores the frozen forecast only after the endpoint
  gate authorizes comparison.

The exact scorer bound into the freeze is retained as
[`scripts/score_prospective_results_frozen_v1.py`](scripts/score_prospective_results_frozen_v1.py).
The current scorer accepts the gate-declared qualifying-report filename for
future contracts, while the frozen copy preserves the byte identity used for
this prospective result.

## Claim boundary

This is one prospective comparison between two constructed replay banks for
one graph policy, target, reward, and trainer. The next decision should widen
the candidate family or move to a new target so that measurement value is
tested over differences large enough to exceed training variation. The result
does not support biological-efficacy claims or a general ranking of molecular
design environments.
