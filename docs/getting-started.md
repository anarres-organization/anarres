# Get started

Anarres helps you qualify native task sources, measure the experience they
produce under a starting policy, and compare compatible candidate environments
before committing the full training budget.

## Install the CLI

=== "Homebrew"

    ```bash
    brew install anarres-organization/tap/anarres
    anarres --version
    ```

=== "Standalone installer"

    ```bash
    curl --proto '=https' --tlsv1.2 -LsSf \
      https://github.com/anarres-organization/anarres/releases/latest/download/anarres-cli-installer.sh | sh
    ```

The [release guide](releases.md) covers Windows, pinned versions, checksums,
archives, source installation, and `PATH` troubleshooting.

## See the workflow

Run the bundled CPU-only example:

```bash
anarres demo
```

The demo qualifies two environments, measures both under the same synthetic
starting policy, checks that their records are comparable, and writes the
portable records to `.anarres/demo/`.

```text
  ✓ Qualified    math-reference-demo-v1
  ✓ Measured     math-reference-demo-v1
  ✓ Compatible   candidate panel

ENVIRONMENT               SIGNAL / 1M   COVERAGE  ADMITTED   REPAIR
math-alternative-demo-v1     214.2857     0.4154         2        1
math-reference-demo-v1       833.3333     0.6533         2        1
```

## Bring an environment

Keep the source in its native format and connect it to the matching adapter:

```bash
anarres init ./candidate-a \
  --adapter <adapter> \
  --revision <immutable-revision> \
  --license <SPDX-identifier>

anarres inspect ./candidate-a
anarres qualify ./candidate-a
```

`inspect` reports the accepted format, source identity, adapter readiness, and
any missing requirements. If that adapter exposes starting-policy execution,
continue with `probe` and `measure`:

```bash
anarres probe ./candidate-a \
  --policy <policy> \
  --policy-revision <revision> \
  --output .anarres/probes/candidate-a

anarres measure .anarres/probes/candidate-a \
  --output .anarres/environments/candidate-a.json
```

Start with the [domain support matrix](domain-support.md) to see which native
formats, probes, and downstream outcome tests are released today. The
[complete CLI guide](cli.md) explains portable records, JSON output, shell
completion, and every command.
