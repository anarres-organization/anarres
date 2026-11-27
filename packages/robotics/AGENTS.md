# Robotics package instructions

This package implements the study-independent robotics adapter described in
`docs/rfcs/0007-portable-robotics-adapter.md`.

- Keep study-specific behavior in the study package under `experiments/robotics/`.
- Preserve native observations, actions, success definitions, resets, and cost units.
- Record reset, simulator, checkpoint, and runtime failures as infrastructure failures.
- Invoke policies only through the external policy-runner protocol.
- Never read downstream training outcomes during qualification, probing, or measurement.
