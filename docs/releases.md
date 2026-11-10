# CLI releases

Anarres publishes native CLI archives from tags named `cli-v<version>`. Each
release contains the binary, license, README, CLI guide, a SHA-256 checksum, and
GitHub build-provenance attestation.

Supported release targets are:

- Linux x86-64 using the GNU C library
- macOS Apple silicon
- Windows x86-64

The source install remains available on every supported Rust host:

```bash
cargo install --path crates/anarres-cli --locked
```

Before creating a release, maintainers update the crate version, run
`make check`, and verify the release build locally. A signed `cli-v<version>`
tag starts the release workflow. Consumers can compare the downloaded archive
with its `.sha256` file and verify provenance with the GitHub CLI:

```bash
gh attestation verify anarres-cli-v0.1.0-aarch64-apple-darwin.tar.gz \
  --repo anarres-organization/anarres
```

Release support expands only after the corresponding target is built and tested
in continuous integration.
