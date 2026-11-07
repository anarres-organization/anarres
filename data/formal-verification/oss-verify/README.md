# OSS Verify release adapter

This adapter qualifies the public assembly-level verification artifacts
released by Theorem Labs. The source consists of Rocq statements about exact
RISC-V binaries, checked against a pinned Linux-process semantics and an
allowlisted axiom contract.

The adapter performs source qualification only. It does not run a proving
model, certify a new proof, or authorize reinforcement learning.

## Pinned source

[`source-pin.json`](source-pin.json) records OSS Verify release `v2026.11.1`,
its immutable Git revision, core index hashes, checker image, Rocq version, and
the exact Linux-process-semantics revision named by the release. The release
contains 20,421 statements across 2,183 entry points. Of these, 526 are proved,
19,656 are open, seven are witnessed false, three are suspected false, and 229
are blocked by the model.

The proved subset supplies checker-oracle and replay fixtures. Open statements
may enter bounded development measurement only after the harness and binaries
for their entire entry point are materialized. Known-false, suspected-false,
model-blocked, withheld, and withdrawn statements are excluded from proving
panels.

## Audit a checkout

Check out the pinned upstream release, then run:

```bash
python data/formal-verification/oss-verify/audit_release.py \
  --source /path/to/oss-verify-proofs \
  --pin data/formal-verification/oss-verify/source-pin.json \
  --output /tmp/oss-verify-audit.json
```

The audit verifies the hashes and sizes of the release metadata, checks the
relations among projects, entry points, binaries, statements, and proofs, and
recomputes every reported count. It writes no files into the upstream checkout.

## Audit the checker runtime

After pulling the digest-pinned checker image, run:

```bash
python data/formal-verification/oss-verify/audit_checker_runtime.py \
  --pin data/formal-verification/oss-verify/source-pin.json \
  --output /tmp/oss-verify-checker-runtime.json
```

The runtime audit checks the local image identity, Rocq version, LPS core
package, `elf-snapshot` executable, and absence of non-loopback routes inside a
container started with `--network none`. It does not replace proof replay.

## Audit checker controls

To exercise the upstream proof, rejection, and statement-mutation controls in
two independent workspaces, run:

```bash
python data/formal-verification/oss-verify/audit_checker_controls.py \
  --source /path/to/oss-verify-proofs \
  --pin data/formal-verification/oss-verify/source-pin.json \
  --output /tmp/oss-verify-checker-controls.json
```

The audit builds only the bounded upstream control suite. It requires positive
proof and refutation fixtures to pass, adversarial candidates to be rejected
for their declared reasons, and every statement-vacuity mutation to be caught.
The two replays start from separate build directories and must agree.

## Build a bounded development panel

After the release audit passes:

```bash
python data/formal-verification/oss-verify/build_development_panel.py \
  --source /path/to/oss-verify-proofs \
  --pin data/formal-verification/oss-verify/source-pin.json \
  --groups 12 \
  --output /tmp/oss-verify-development-panel.json
```

Selection is deterministic and outcome-blind within the eligible set. An entry
point is eligible when it has at least one proved statement for checker replay
and at least one open statement for development measurement. The entry point,
not an individual statement, is the grouping unit. Hash ordering selects one
entry point per library before reusing a library. The output is a development
artifact and cannot be promoted to a qualification or prospective target
without a new frozen protocol.

## Remaining executable gates

Before a frozen-policy measurement, each selected entry point still requires:

1. release-asset retrieval with hash verification
2. checker execution in the pinned digest with networking disabled
3. successful replay of a published proof
4. rejection of an empty submission, `Admitted`, and an unapproved axiom
5. statement-mutation and binary-mutation rejection
6. repeated clean-reset agreement
7. wall-time, memory, token, and tool-call measurement.

The Linux-process model is part of the claim. Its documented assumptions and
unmodeled behavior must remain visible in every downstream result.
