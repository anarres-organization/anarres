# CLI releases

Anarres publishes native CLI artifacts from tags named
`anarres-cli-v<version>`. The release workflow is generated and validated by
`dist` and produces platform archives, checksums, shell and PowerShell
installers, a Homebrew formula, and a source archive.

Domain adapters are released independently from the native binary. The CLI
discovers installed `anarres-<name>` executables and validates their versioned
descriptor before execution. A CLI archive therefore does not bundle Python,
simulators, model runtimes, or domain evidence.

Supported release targets are:

- Linux x86-64 and ARM64 using the GNU C library
- macOS Apple silicon and x86-64
- Windows x86-64

Install the latest release on macOS or Linux:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
```

Restart the shell if prompted, then verify the installation:

```bash
anarres --version
```

Install it on Windows from PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.ps1 | iex"
```

Open a new PowerShell session, then verify the installation:

```powershell
anarres --version
```

Inspect the shell installer without executing it:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | less
```

For a reproducible installation, replace `latest/download` with a release tag:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/download/anarres-cli-v0.1.0/anarres-cli-installer.sh | sh
```

The source install remains available on every supported Rust host after cloning
the repository:

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres
cargo install --path crates/anarres-cli --locked
```

Rerun the standalone installer to update. It installs to `$CARGO_HOME/bin`, or
`$HOME/.cargo/bin` when `CARGO_HOME` is unset. Remove the `anarres` binary from
that directory to uninstall a standalone installation. Package-manager installs
should instead be updated or removed through the same package manager.

Before creating a release, maintainers update the crate version and changelog,
run `make check` and `make release-smoke`, and inspect the generated plan:

```bash
dist generate
dist plan --tag anarres-cli-v0.1.0
```

A signed `anarres-cli-v<version>` tag starts the release workflow. Pull
requests exercise the same artifact graph without publishing. Consumers can
compare downloads with `sha256.sum` and verify the published build provenance
with the GitHub CLI:

```bash
gh attestation verify anarres-cli-aarch64-apple-darwin.tar.xz \
  --repo anarres-organization/anarres
```

The release is accepted only when the native archives, installers, completion
generation, built-in fixture workflow, startup budget, and clean installation
of every maintained domain adapter pass in continuous integration. Platform
support expands only after the corresponding target is built and tested there.
