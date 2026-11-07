# Data systems

Data systems turn heterogeneous task sources into reproducible learning
environments. They own acquisition, normalization, qualification, provenance,
and candidate construction. They do not choose claim-bearing environments after
observing training outcomes.

Large task collections remain in external versioned stores. This directory
contains maintained processing code, small fixtures, and public documentation.

The active [environment-processing project](environment-processing/README.md)
defines the scientific contracts for qualification and policy-relative
measurement. Its [implementation plan](environment-processing/ROADMAP.md)
tracks the path from the current reference implementation to independently
confirmed candidate environments and downstream RL validation.

Domain adapters preserve native task and verifier contracts before producing
shared environment records. The
[formal-verification adapters](formal-verification/README.md) begin with pinned
OSS Verify and Vero sources. They keep native checker semantics, artifact
identity, and repository or statement grouping explicit.
