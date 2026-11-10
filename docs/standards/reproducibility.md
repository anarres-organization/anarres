# Reproducibility standard

A released experiment must identify enough information to reconstruct its main scientific claims.

## Required elements

- Experiment and protocol version
- Primary estimand and experimental units
- Development and prospective partitions
- Source and task identities
- Model, tokenizer, and software revisions
- Training and evaluation contracts
- Random seeds
- Generated-token accounting
- Checkpoint schedule
- Infrastructure and scientific failure accounting
- Artifact references and content digests
- Analysis entry point
- Known deviations and superseded runs

## Prospective work

Forecasts and candidate identities are frozen before prospective outcomes are inspected. A correction creates a new artifact with an explicit relationship to the previous version. It does not modify the original freeze in place.

## Failure semantics

Infrastructure failures, verifier failures, context-limit events, scientific reward zero, and excluded observations are distinct outcomes. Aggregation must not silently convert between them.

## Repository checks

Software conformance and scientific reproduction remain separate:

```bash
make check
make study-check
```

The first command tests maintained code, schemas, and interfaces. The second
recomputes compact claim-bearing records and maintained adapter outputs, then
checks that reproduction leaves tracked artifacts unchanged. The extended
suite adds exhaustive isolated releases:

```bash
make study-check-extended
```
