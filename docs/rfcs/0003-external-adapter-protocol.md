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
`adapter doctor` validates the complete descriptor. A workflow command launches
the adapter once and prefixes the forwarded arguments with the runtime protocol
version and expected adapter name:

```text
--anarres-adapter-protocol 2 --anarres-adapter-name <name>
```

The adapter validates and removes this handshake before parsing its own
arguments. Direct adapter invocation remains supported. An adapter that does
not implement the selected runtime protocol rejects the unknown arguments
before opening study artifacts.

Protocol 2 introduces this single-launch handshake. Protocol 1 adapters used a
separate descriptor process before each workflow and are intentionally
incompatible with a protocol 2 native CLI. Reinstalling the adapter updates both
its descriptor and runtime entrypoint.

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
descriptor permits a complete installation audit without opening study
artifacts or running a measurement. The runtime handshake preserves protocol
and identity checks without paying for a second adapter process on each command.

Executable discovery inherits the user's `PATH` trust boundary. `adapter list`
reports shadowed names, and `adapter doctor` shows the exact executable selected
before a workflow runs. Names containing path separators, shell syntax, or
unsupported characters are rejected.

The first protocol does not define a remote registry, package manager, daemon,
dynamic-library ABI, telemetry service, or automatic installation. Those
features require separate evidence and an RFC.
