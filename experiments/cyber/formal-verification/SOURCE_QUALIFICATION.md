# OSS Verify source qualification

**Audit date:** 2026-11-07

This record qualifies the machine-readable indexes of Theorem Labs' OSS Verify
release `v2026.11.1` for bounded harness development. It does not qualify the
runtime, a proving policy, or a downstream training environment.

## Pinned release

| Component | Immutable identity |
| --- | --- |
| OSS Verify | tag `v2026.11.1`, commit `6d15d8457aeecc77db61395ec8bcb3879b1d0f8b` |
| Release date | 2026-11-05 |
| Rocq | 9.2.0 |
| Linux-process semantics | commit `f1006fe8178338a499b5e5c41be83006c4edd058` |
| Checker image | `ghcr.io/theorem-labs/oss-fuzz-theorems-checker@sha256:063f93261f11ba449f1c3825884fadc65cf1fc836d4a3ee534633211abbdc3eb` |
| Runner image | `ghcr.io/theorem-labs/oss-fuzz-theorems-runner@sha256:2eb5afc7b37095cbab0e290966b991cda8bdedbefe8fdb4ce44f56d0c30834c0` |

The content hashes and sizes of the release metadata, five index tables,
allowed-axiom list, and checker Dockerfile are recorded in the
[source pin](../../../data/formal-verification/oss-verify/source-pin.json).

## Reproduced inventory

The [release audit](../../../data/formal-verification/oss-verify/audit_release.py)
verified artifact identity, metadata, index schemas, cross-index references,
and agreement between the proof index and proved statement statuses.

| Unit | Count |
| --- | ---: |
| Projects | 1,388 |
| Entry points | 2,183 |
| Published or indexed binaries | 8,718 |
| Statements | 20,421 |
| Proved statements | 526 |
| Entry points with proofs | 90 |
| Libraries with proofs | 32 |
| Open statements | 19,656 |
| Statements blocked by the model | 229 |
| Witnessed-false statements | 7 |
| Suspected-false statements | 3 |

The release exposes 60 entry points that contain both a published proved
statement and an open statement. These groups can support a bounded development
panel in which the published proof is a checker oracle and the open statement
is a measurement task. The deterministic panel builder selects one entry point
per library before reusing a library, which preserves repository diversity and
keeps related statements grouped.

## Runtime bootstrap

The exact checker image was retrieved at its pinned digest and started with
Docker networking disabled. The
[runtime audit](../../../data/formal-verification/oss-verify/audit_checker_runtime.py)
verified the 1,329,799,572-byte image identity, Rocq 9.2.0, the installed LPS core
package, and the `elf-snapshot` executable. The probe exposed no IPv4 routes or
non-loopback IPv6 routes. The coturn release archive was also fetched with the
upstream tool, which verified its archive and eight binary hashes.

These checks qualify image startup and one release-asset path. They do not
qualify proof replay or the selected development panel.

The bounded upstream checker suite was then replayed twice from independent
build directories with networking disabled. All 32 positive proof and
refutation controls passed, all seven adversarial candidates were rejected for
their declared reasons, and all 13 statement-vacuity mutations were caught.
The adversarial controls include admitted proofs, injected and hidden axioms,
a doctored statement, and a proof of the wrong statement. Both clean replays
agreed.

## Scientific role

The assembly-level source is useful for three distinct purposes:

1. checker and reset qualification using published proofs
2. frozen-policy measurement on open statements with exact binary and statement
   identities
3. later testing of proof reuse, repository context, and cost at a production
   scale.

The proved and open statements do not form interchangeable independent tasks.
Statements share binaries, entry points, proof libraries, and the same formal
semantics. Entry point is the minimum grouping unit for development. Library is
the minimum partitioning unit for held-out comparisons.

## Remaining gates

Full harness qualification remains pending. The next pass must materialize
every selected panel asset, replay published proofs in the pinned checker,
exercise binary and selected-harness mutation tests, and measure clean-reset
reliability and cost on the development panel. Only then can a starting-policy
probe determine whether the open statements provide enough valid and mixed
outcome support for an intervention.

The checker establishes statements relative to the pinned Linux-process model,
binary builds, allowed axioms, and environmental assumptions. Results must keep
those conditions visible and cannot be described as source-level correctness of
an entire library.
