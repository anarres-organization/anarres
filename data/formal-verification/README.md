# Formal-verification source processing

This directory contains source adapters and qualification tools for executable
formal-verification environments. The tools preserve each proof assistant's
native checker contract and produce compact, content-addressed records for the
formal-verification studies under `experiments/`.

The first adapter covers Theorem Labs' public OSS Verify release. It validates
the release indexes, binary and statement identities, proof references, Rocq
version, Linux-process-semantics revision, and checker image before producing a
development panel. The panel remains grouped by library and entry point so that
related statements are not treated as independent tasks.

See [oss-verify/README.md](oss-verify/README.md) for the assembly-level release
adapter and [vero/README.md](vero/README.md) for the repository-level Lean
adapter.
