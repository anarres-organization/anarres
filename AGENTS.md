# Agent instructions

These instructions apply to the entire Anarres repository. A nested `AGENTS.md` may add stricter local rules for code in its directory.

## Purpose

Anarres supports research on predictable post-training. Preserve the distinction between reusable implementation, data systems, and domain-organized experiments.

## Required behavior

- Never fabricate measurements, citations, manifests, hashes, or artifact locations.
- Never convert an infrastructure failure into scientific reward zero.
- Never inspect prospective outcomes before the governing protocol permits it.
- Never change a frozen protocol, panel, forecast, or evaluation contract in place.
- Preserve source revisions, task identities, licenses, and content hashes.
- Add or update tests whenever behavior changes.
- Keep secrets, machine-specific credentials, large artifacts, checkpoints, and generated outputs out of Git.
- Do not commit credentials, machine-specific paths, transient logs, or cluster-specific operations.
- Prefer released configurations, compact results, and reproducible analyses over raw execution state.
- Put reusable behavior in a package. Put source processing in `data/`. Put study-specific work in the relevant domain under `experiments/`.
- Do not copy an implementation between experiments when it can be shared through a maintained interface.
- Prefer clear medium-length prose. Avoid inflated claims and unexplained internal terminology.

## Change discipline

An RFC is required for a breaking public API change, a shared-schema change, a new maintained package, or a change to an organization-wide scientific invariant. It is not required for ordinary bug fixes, documentation, tests, or experiment-local analysis.

Before finishing a change, run:

```bash
make check
```

If the relevant integration environment is unavailable, state exactly which check was not run and why.

## Scientific integrity

- Development and prospective partitions must be explicit.
- Candidate construction must not read claim-bearing outcomes.
- Scientific failures and infrastructure failures must be reported separately.
- Figures and tables must be regenerable from identified inputs.
- Exploratory results must not be relabeled as prospective.
- Failed experiments may be preserved as evidence, but transient logs do not belong in the source repository.

## External artifacts

Use an artifact reference containing a URI, SHA-256 digest, media type, size, license, and producing run. Mutable aliases such as `latest` must not be inputs to claim-bearing work.
