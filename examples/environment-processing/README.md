# Environment-processing example

This CPU-only example demonstrates the reference contract without downloading
a model or launching a sandbox. `probe.json` and `probe-alternative.json`
represent two candidates measured under the same synthetic starting policy and
probe contract.

`probe-run/` shows the interchange produced by an environment runtime. Its
`attempts.jsonl` contains one row per raw policy attempt. The Rust CLI streams
those rows, validates exact group membership, and derives unnormalized
leave-one-out admitted advantage mass rather than asking the producer to
precompute it.

The fixture contains:

- Two scientifically valid mixed groups
- One valid but zero-variance reserve group
- One verifier-invalid group
- One infrastructure-invalid group

Run `make example` from the repository root. The output is ignored by Git and written to `.anarres/example/environment.json`.

The same workflow can be run directly after installing the native command:

```bash
anarres qualify examples/environment-processing/probe.json
anarres measure examples/environment-processing/probe.json \
  --output .anarres/example/environment.json
anarres validate .anarres/example/environment.json
anarres measure examples/environment-processing/probe-alternative.json \
  --output .anarres/example/environment-alternative.json
anarres design \
  .anarres/example/environment.json \
  .anarres/example/environment-alternative.json
```

The raw-attempt path uses the same commands with a directory input:

```bash
anarres qualify examples/environment-processing/probe-run
anarres measure examples/environment-processing/probe-run \
  --output .anarres/example/raw-attempt-environment.json
anarres validate examples/environment-processing/probe-run \
  .anarres/example/raw-attempt-environment.json
```

The fixture is synthetic. It tests contract behavior and does not support a scientific claim. The
`source_revision` in `probe.json` is the SHA-256 digest of the exact bytes in `source.json`.
