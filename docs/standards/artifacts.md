# Artifact policy

Git stores code, schemas, documentation, small fixtures, and manifests. It does not store model weights, checkpoints, rollout traces, large datasets, generated results, or mutable experiment directories.

## Required reference fields

Every external artifact reference records:

- Immutable URI or revision
- SHA-256 digest
- Media type
- Size in bytes
- License or access terms
- Producing run when applicable

Claim-bearing inputs may not use mutable aliases such as `latest`.

## Intended storage

- GitHub for source, schemas, small fixtures, and manifests
- Hugging Face for released datasets and models with cards
- Object storage or DFS for checkpoints, rollouts, traces, and large results
- OCI registries for containers pinned by digest
- Experiment trackers for live telemetry, not canonical evidence

Machine-specific storage paths and hostnames must not appear in released manifests.
GitHub Releases or a research artifact repository should carry compact experiment
bundles. Hugging Face repositories should carry models and datasets with model or
dataset cards.
