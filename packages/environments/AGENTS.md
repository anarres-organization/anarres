# Environment package instructions

This package implements reusable environment ingestion, qualification, measurement, and composition.

- Preserve infrastructure outcomes separately from task rewards.
- Never tune qualification gates against claim-bearing RL outcomes.
- Require stable task identities and source revisions.
- Keep policy-relative measurements tied to their exact rollout contract.
- Add tests for zero-signal, zero-variance, verifier-invalid, and infrastructure-invalid cases.
- Reusable source parsing belongs under `data/`. Experiment-specific adapters remain with the relevant domain until their interface is stable.
