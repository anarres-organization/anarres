# Retrospective three-source robotics analysis

**Status:** retrospective evidence; not a prospective forecast.

This analysis normalizes candidate-decision panels from three open robotics
projects:

- [Calibra](https://github.com/Calibra-Robotics/Calibra), dataset observability
  and coreset selection for imitation learning;
- [CuraEval](https://github.com/jiuyixu25/CuraEval), demonstration curation on
  mixed-skill robot data;
- [Mulligan](https://github.com/ankile/mulligan), performance-guided on-robot
  data collection.

The normalized cut contains 31 candidate-decision panels, 111 candidate arms,
and eight task or dataset contexts. Outcomes retain their native definitions.
Only within-panel ordering and normalized regret are compared across sources.

## Held-out-context result

| Rule | Pair ordering | Mean normalized regret | Top-choice credit |
| --- | ---: | ---: | ---: |
| Uninformed tie | 50.0% | 0.467 | 36.3% |
| Practical measurement rule | **65.4%** | **0.272** | **58.3%** |
| Fitted measurement ridge | 59.9% | 0.324 | 43.8% |

The practical rule uses interpretable, pre-outcome concepts: targeted
information, diversity, quality correction, reliability, missingness, and
exposure. It reduces regret relative to an uninformed choice on this cut.

The fitted ridge model does not beat the practical rule. A source-label negative
control is also competitive, which warns that source structure and panel
pairing can explain apparent performance. The result therefore does not
authorize a larger neural model or a general robotics selector claim.

## Normalization rules

1. Candidate identities, policies, budgets, and target endpoints are preserved.
2. Native utilities are normalized only within each decision panel.
3. Source, context, policy, and panel identifiers define held-out groups; they
   are never predictive features.
4. Source-native measurements are mapped by meaning and converted to
   within-panel ranks.
5. Missing measurements remain explicit.
6. Label-only fits are negative controls, not evidence.

The complete compact metrics are in [`summary.json`](summary.json).

## Limits

This analysis uses already published outcomes. It can test model form and expose
confounds, but it cannot establish prospective accuracy. CuraEval also lacks
aggregate seed rows for some deterministic candidates, so its uncertainty
support is incomplete. The next strong test must freeze measurements and a
decision on a new panel before outcomes are opened.
