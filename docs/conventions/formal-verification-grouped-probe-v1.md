# Formal-verification grouped probe v1

- Stability: development
- Revision: `v1-development`
- Scope: repeated machine-checked attempts grouped by native verification unit

This convention measures an executable formal-verification environment under a
frozen starting policy, agent scaffold, verifier, and interaction budget. The
native record must preserve repository, task, proof mode, verifier identity,
strict validity, infrastructure status, token usage, and containment evidence.

Compilation alone is not a strict success. The native verifier contract must
reject unfilled proofs, disallowed axioms, weakened statements, and invalid
runtime outcomes. Infrastructure-invalid attempts remain missing or invalid
observations rather than unsuccessful proofs.

## `usable_signal_density`

Unnormalized leave-one-out absolute strict-reward advantage mass per million
charged model tokens. Unit: `advantage_mass_per_million_model_tokens`. The
coordinate has contextual direction because nonzero signal is necessary for
the grouped update, while density alone does not establish downstream utility.

## `effective_verification_coverage`

Normalized effective sample size of strict-reward advantage mass across native
verification groups. Unit: `fraction`. Zero admitted mass yields zero effective
coverage. The grouping unit and nesting structure must be declared by the
measurement contract.

## `mean_model_tokens_per_attempt`

Arithmetic mean of actual charged input and output tokens over
infrastructure-valid attempts. Unit: `model_tokens_per_attempt`. Token limits
and controller stop semantics remain part of the native interaction contract.

## Readiness

A valid zero-signal measurement is different from an invalid execution. An
adapter may report exact zero coordinates after every infrastructure and
verifier check passes, while an error-level support check marks the profile
unready for candidate ranking or downstream training.
