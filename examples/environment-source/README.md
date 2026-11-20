# Native environment source

`anarres.toml` is the narrow envelope that connects native environment files
to an installed Anarres adapter. It does not replace an OpenEnv package, Harbor
task, Gymnasium registration, robot dataset, legal matter panel, molecular
bank, atomistic dataset, or proof repository.

The required fields answer six questions before execution:

1. Which candidate environment is this?
2. Which scientific domain owns its interpretation?
3. Which adapter understands the native files?
4. Which native format does that adapter expect?
5. Where are the unchanged source files?
6. Which immutable revision and license identify those files?

The example contains a small Harvey-LAB-shaped legal source that can be
qualified without a model, API credential, or GPU. Install the legal adapter
from the checkout, then inspect and qualify the unchanged native files:

```bash
uv tool install ./packages/legal
anarres inspect examples/environment-source/anarres.toml
anarres qualify examples/environment-source/anarres.toml
```

Create the same envelope beside another Harvey LAB checkout without writing
TOML manually:

```bash
anarres init /path/to/harvey-labs \
  --adapter legal \
  --revision git:<commit> \
  --license MIT
```

Relative source paths resolve from the directory containing `anarres.toml`.
Remote URIs remain adapter-owned. Credentials and policy endpoints do not
belong in the manifest; adapters read credentials from their documented runtime
mechanism, and `anarres probe` receives the starting-policy identity explicitly.
