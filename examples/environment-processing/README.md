# Environment-processing example

This CPU-only example demonstrates the reference contract without downloading a model or launching a sandbox.

The fixture contains:

- Two scientifically valid mixed groups
- One valid but zero-variance reserve group
- One verifier-invalid group
- One infrastructure-invalid group

Run `make example` from the repository root. The output is ignored by Git and written to `.anarres/example/environment.json`.

The fixture is synthetic. It tests contract behavior and does not support a scientific claim. The
`source_revision` in `probe.json` is the SHA-256 digest of the exact bytes in `source.json`.
