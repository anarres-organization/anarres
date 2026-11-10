# First-run evaluation

Anarres evaluates the CLI with people who have not contributed to its
implementation. The goal is to find installation, terminology, and recovery
problems before adding more commands.

## Session

Give a participant the repository URL and ask them to complete these tasks
without a walkthrough:

1. Install `anarres` and print its version.
2. Run the bundled CPU-only example through `qualify`, `measure`, and
   `validate`.
3. Explain what the generated record contains and what it does not claim.
4. Discover installed adapters and diagnose one missing adapter.
5. Locate the command reference and report one confusing step.

Do not provide model credentials, private evidence, or a repository checkout
unless the participant chooses a source installation. A successful session
requires no GPU and no network access after installation.

## Measures

Record the operating system, installation method, CLI version, time to the
first validated record, commands that required documentation, the first
blocking error, and whether the participant could explain the boundary between
the native CLI and a domain adapter. Do not collect shell history, environment
variables, credentials, or unreleased artifacts.

The initial release target is a validated bundled record within ten minutes,
with no maintainer intervention. Failures become documentation or product
issues before new surface area is added.

## Reporting

Use the first-run feedback issue form for public reports. Include the smallest
safe reproduction and redact machine-specific paths or source data. Security
issues follow [`SECURITY.md`](../SECURITY.md) rather than the public issue
tracker.
