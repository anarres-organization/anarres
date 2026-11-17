# Runbook

All steps are free and local except the model calls, which use an existing
allowance and no paid API. No step needs a GPU. No step trains a model.

## Offline steps

1. `python3 scripts/build_fixtures.py` writes the fixtures with seed 20261116.
2. `python3 scripts/run_verifier_controls.py` runs the exact scorer on gold,
   corrupted, and unparseable answers, and the lexical checkers on the
   transcripts.
3. `python3 scripts/make_prompts.py` and
   `python3 scripts/make_policy_judge_prompt.py` write the prompts in `prompts/`.
4. `python3 scripts/score_runs.py` scores the saved model outputs in
   `results/raw/` and writes the score files in `results/`.
5. `python3 scripts/make_profile_inputs.py` writes the profile inputs.
6. `scripts/run_anarres_flow.sh` runs `anarres measure`, `validate`, and
   `design` on them with the installed CLI (version 0.4.0 was used).

## Model-call steps

Each prompt in `prompts/` is sent once per subject. The raw reply is saved
unchanged in `results/raw/`. A reply that cannot be parsed is recorded as
invalid and kept out of the pass counts. A failed call is recorded as an
infrastructure failure and is never scored as a failed check.

## Rules

- Never change `scripts/checkers.py` after outcomes are read. A rule change is
  a new version.
- Keep prompts identical across subjects.
- Name the route and model for every call in the results.
