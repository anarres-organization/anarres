# Prospective artifacts

This directory contains the exact frozen forecasts and immutable post-outcome scores for both prospective scale tests.

The cost/admission predictor and numerical 8B forecast were serialized before observing the 8B RL outcomes. After that test was scored, the ρ–H representation was developed using the 1.7B, 4B, and 8B results. Its numerical 14B curves, rankings, and uncertainty envelope were then frozen before inspecting the 14B held-out outcomes. Four-scale leave-one-scale-out analyses were run only after the 14B forecast had been scored.

The uniform-mixture manifest, pre-RL measurement, and forecast were also frozen before its RL outcomes. That stress test remains separate from the controlled four-cell forecast.

Key files:

- `8b_numerical_forecast.json` and `8b_frozen_forecast_score.json`
- `14b_final_frozen_forecast.json` and `14b_final_frozen_forecast_score.json`
- `14b_predictor_family_freeze.json`
- `8b_stage_d_decision.json` and `14b_stage_d_decision.json`
- `source_object_hashes.json`

The recorded 14B source hashes begin with `7fad0619ecae` for the forecast and `8d755d276f08` for its score, matching the frozen study record. Machine-specific analysis roots are represented by `${ANALYSIS_ROOT}`. No coefficient, prediction, ranking, uncertainty value, observation, or score changes under that portable path substitution.
