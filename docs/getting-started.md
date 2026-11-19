# Get started

Anarres helps you qualify native task sources, measure the experience they
produce under a starting policy, and compare compatible candidate environments
before committing the full training budget.

## Install the CLI

=== "Homebrew"

    ```bash
    brew tap \
      anarres-organization/tap
    brew install anarres
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
It also writes `.anarres/.gitignore`, keeping generated records out of a fresh
project's Git status.

```text
  ✓ Qualified    math-reference-demo-v1
  ✓ Measured     math-reference-demo-v1
  ✓ Compatible   candidate panel

ENVIRONMENT               SIGNAL / 1M   COVERAGE  ADMITTED   REPAIR
math-alternative-demo-v1     214.2857     0.4154         2        1
math-reference-demo-v1       833.3333     0.6533         2        1
```

## Bring an environment

Homebrew and the standalone installer provide the core CLI. To work with native
domain data, clone Anarres and install the matching adapter first:

```bash
git clone https://github.com/anarres-organization/anarres.git
cd anarres
uv tool install ./packages/legal  # choose the adapter path for your domain
anarres adapter list
```

The [adapter guide](adapters.md) lists every valid adapter name and installation
path. Keep the source in its native format and connect it to that adapter:

```bash
anarres init ./candidate-a \
  --adapter <adapter> \
  --revision git:<full-commit> \
  --license <SPDX-identifier>

anarres inspect ./candidate-a
anarres qualify ./candidate-a
```

Use a full commit, content digest, or immutable release identifier for the
revision. `inspect` confirms the manifest, adapter, and declared capability; it
does not validate the native files. `qualify` performs that validation. If the
adapter exposes starting-policy execution,
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

Most maintained adapters currently stop at native source qualification. Only
the molecular adapter exposes the shared probe path, and it requires the native
policy and scientific artifacts described by that adapter. Use `anarres demo`
for a zero-setup run through qualification, measurement, and comparison.
