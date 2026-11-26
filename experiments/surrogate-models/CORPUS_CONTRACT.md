# Cross-domain intervention corpus

`CORPUS_INVENTORY.json` and `CORPUS_RECORDS.jsonl` form the first read-only
index of released Anarres intervention evidence. The manifest contains source
digests and release counts. The JSON Lines file contains one intervention per
line so it can be streamed without loading the full corpus. Together they make
the current evidence usable for surrogate-model research without changing the
scientific contract of any contributing study.

## What one record means

A record is either:

- one independently trained intervention when a study releases seed-level runs
- one published candidate-arm aggregate when only a paper-level result is
  available.

The `evidence_level` field makes that distinction explicit. Tasks, checkpoints,
targets, criteria, traces, and evaluation episodes remain nested evidence. They
are never counted as independent training interventions.

Each record contains a stable pointer to its native artifact, a SHA-256 digest
through the source table, the candidate panel and lineage, information available
before the outcome, the native outcome and direction, cost status, and grouping
keys. Missing cost remains missing. Infrastructure failure is not encoded as a
zero outcome.

## What may be compared

Candidate outcomes may be compared only within the same declared panel. Native
units are preserved. Panel-normalized values already released by a contributing
study are retained, but the inventory does not create a universal utility label.

Primary evaluation must hold out complete studies or domains. Every seed,
checkpoint, target, and evaluation associated with one candidate lineage stays
in the same split. Public-study aggregates and independent training runs must be
reported separately.

## Current release

The inventory indexes:

- 101 seed-level interventions across mathematics, robotics, legal reasoning,
  and materials science;
- 3,540 published candidate-arm aggregates from the materials-science and
  finance retrospective bridges; and
- five programs that have useful qualification or measurement evidence but no
  released candidate-training labels for this task.

The large retrospective bridges are valuable for representation and ordering
tests, but they do not turn publication-conditioned evidence into thousands of
independent experiments. Study-macro and domain-macro results remain primary.

This release indexes structured prediction-time evidence and the native files
that contain it. It does not yet package raw trajectories, video, structures,
or other large modality artifacts. Those assets require a separate manifest
with their own licenses, digests, availability times, and reconstruction tests
before they may enter a multimodal baseline.

## Rebuild and verify

```bash
python experiments/surrogate-models/build_corpus_inventory.py
python experiments/surrogate-models/build_corpus_inventory.py --check
python -m unittest experiments/surrogate-models/test_build_corpus_inventory.py
```

The builder reads released artifacts only. Adding a source requires an explicit
extractor or allowlist entry, a declared evidence level, grouping, chronology,
cost status, and tests. A shared repository-wide schema should follow evidence
of compatibility across studies rather than be imposed by this inventory.
