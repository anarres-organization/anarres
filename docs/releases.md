# CLI releases

Anarres publishes native CLI artifacts from tags named
`anarres-cli-v<version>`. The release workflow is generated and validated by
`dist` and produces platform archives, checksums, shell and PowerShell
installers, a Homebrew formula, and a source archive.

Domain adapters are released independently from the native binary. The CLI
discovers installed `anarres-<name>` executables and validates their versioned
descriptor before execution. A CLI archive therefore does not bundle Python,
simulators, model runtimes, or domain evidence.

## Install

Supported release targets are:

- Linux x86-64 and ARM64 using the GNU C library
- macOS Apple silicon and x86-64
- Windows x86-64

Install with Homebrew on macOS or Linux:

```bash
brew tap \
  anarres-organization/tap
brew install anarres
```

Install the latest release on macOS or Linux:

```bash
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
```

Restart the shell if prompted, then verify the installation:

```bash
anarres --version
```

## Troubleshooting

### Command not found

First confirm that the installation completed. For Homebrew:

```bash
brew list --versions anarres-organization/tap/anarres
"$(brew --prefix)/bin/anarres" --version
```

For the standalone installer:

```bash
"${CARGO_HOME:-$HOME/.cargo}/bin/anarres" --version
```

If the direct command works, open a new terminal. To update the current shell
immediately, add the standalone binary directory to `PATH`:

```bash
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$PATH"
```

If `brew install` stopped with a Command Line Tools error, the formula was not
installed. Follow Homebrew's printed update instructions or use the standalone
installer.

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
  https://github.com/anarres-organization/anarres/releases/download/anarres-cli-v0.4.0/anarres-cli-installer.sh | sh
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

## Maintainer release checklist

Before creating a release, maintainers update the crate version and changelog,
run `make check`, `make release-smoke`, and `make benchmark`, then inspect the
generated plan:

```bash
dist generate
dist plan --tag anarres-cli-v0.4.0
```

After the GitHub release passes its artifact checks, copy the generated
`anarres.rb` into the official
[`homebrew-tap`](https://github.com/anarres-organization/homebrew-tap), run its
macOS and Linux checks, and merge that update before advertising the new
Homebrew version.

## Verify downloads

A versioned `anarres-cli-v<version>` tag starts the release workflow. Pull
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
