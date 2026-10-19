# Phase C prerequisites

Phase C (the model-based warm-start floor probe) is blocked until a host meets
the requirements below. These are environment requirements, not science: none of
them changes the frozen protocol. This file is generic on purpose; specific host
names, paths, and operational state do not belong in the repository.

## Required to run Phase B fixture materialization and Phase C probe

1. **Container runtime.** CyberGym packages vulnerable targets as containers
   (ARVO / OSS-Fuzz Docker images) and runs a local-only submission service.
   A working OCI runtime (Docker, or rootless Podman) is mandatory. No fixture
   can be materialized, graded, reset, or contained without one. A host with no
   container runtime cannot run any part of Phase B or C.

2. **Free disk.** CyberGym benchmark data is ~240 GB and the dynamic server data
   is larger; built images add more. Provision well above the retained-storage
   budget (`feasibility_budget.maximum_retained_storage_bytes` = 1 TiB) on a
   filesystem that is not already near capacity. Do not stage onto a shared
   filesystem at or near 100% use.

3. **GPU for serving the warm start.** The 8B warm start
   (`nvidia/Nemotron-Terminal-8B`, ~16.4 GB bf16) is served for rollouts. One
   modern data-center GPU is sufficient to serve it; respect the per-node GPU
   budget and check load before claiming GPUs.

4. **Warm-start weights downloaded and digest-verified.** Download at the pinned
   revision, verify sha256 against `WARM_START_PROVENANCE.md`, record the local
   artifact digest in the protocol, and confirm exact match to the agentic warm
   start.

5. **Network egress policy.** The agent network must be egress-denied by default
   with only the isolated task network reachable, per `CONTAINMENT_SPEC.md`.

## Order once a qualifying host is available

1. Download + digest-verify the warm start (item 4).
2. Materialize the frozen 48-task probe subset (and the >= 246 target partition)
   via the extended `freeze_development_candidates.py`, with the identity map so
   the disjointness audit is resolved rather than UNRESOLVED.
3. Build containment; run oracle / no-op / repeated-reset and the containment
   checks, recording results in a fixture manifest (`fixture-manifest.template.json`).
4. Only after all static fixture gates pass: run the frozen two-view G=8 probe,
   compute strict success + rho + H + mixed-group + two-view reliability, and
   consult `reliability_oc.json` for the abstention rule.
5. Emit one decision per `DECISION_TREE.md`: proceed / external-target-only /
   unmeasurable. This is never an RL authorization.
