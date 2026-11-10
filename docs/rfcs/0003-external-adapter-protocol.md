# RFC 0003: External adapter protocol

- Status: accepted
- Date: 2026-11-09

## Context

The native CLI validates records and performs fast local operations without a
domain runtime. Domain workflows still need independent implementations in
Python and other ecosystems. Adding one built-in command per domain would make
the Rust core depend on the release cadence and command structure of every
study. Loading adapters in process would introduce language-specific packaging
and stability constraints.

Anarres needs a small extension boundary that keeps the core stable, gives
installed adapters a consistent user interface, and preserves each study's
scientific ownership.

## Decision

An adapter is a standalone executable named `anarres-<name>` on `PATH`. The
name is a lowercase slug containing letters, digits, and interior hyphens. The
native CLI discovers exact executable names without invoking a shell.

Every adapter implements a side-effect-free descriptor command:

```bash
anarres-<name> --anarres-adapter-descriptor
```

The command prints one `anarres.adapter-descriptor.v1` JSON object. The
descriptor identifies the adapter, protocol version, domain, executable,
supported profile schemas, capabilities, and native measurement contracts.
The CLI validates the descriptor before forwarding a workflow command.

The management interface is:

```text
anarres adapter list
anarres adapter doctor <name>
anarres adapter run <name> -- <arguments...>
```

`anarres <name> <arguments...>` is equivalent to the explicit run form when
`<name>` is not a built-in command. Built-in commands always take precedence.
Arguments are forwarded literally, and the adapter's exit status is preserved.

Discovery is local and read-only. The CLI does not download adapters, search a
repository checkout, import their libraries, or modify the environment. Python
adapters can be installed as isolated tools, while adapters written in other
languages follow the same executable protocol.

## Consequences

New domains can add commands without changing or releasing the Rust core.
Adapters retain their own dependencies, tests, and scientific contracts. The
descriptor permits compatibility checks without opening study artifacts or
running a measurement.

Executable discovery inherits the user's `PATH` trust boundary. `adapter list`
reports shadowed names, and `adapter doctor` shows the exact executable selected
before a workflow runs. Names containing path separators, shell syntax, or
unsupported characters are rejected.

The first protocol does not define a remote registry, package manager, daemon,
dynamic-library ABI, telemetry service, or automatic installation. Those
features require separate evidence and an RFC.
