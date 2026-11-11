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

The example uses an OpenEnv-shaped source, but it is a format example rather
than a bundled runtime. `anarres inspect` reports whether the named adapter is
installed and whether it declares qualification and policy-probe support for
the requested format.

```bash
anarres inspect examples/environment-source/anarres.toml
```

Relative source paths resolve from the directory containing `anarres.toml`.
Remote URIs remain adapter-owned. Credentials and policy endpoints do not
belong in the manifest; adapters read credentials from their documented runtime
mechanism, and `anarres probe` receives the starting-policy identity explicitly.
