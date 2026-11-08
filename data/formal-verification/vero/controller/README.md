# Isolated Vibe controller

This directory contains the complete user-level Vibe configuration for the
frozen Vero development probe. The launcher copies only these files into a new
private `VIBE_HOME` for each attempt. It does not load the operator's Vibe home,
credentials, agents, skills, plugins, hooks, MCP servers, or project
configuration.

The Lean agent follows Mistral's published local Leanstral configuration. Its
paired 1,200-second shell timeouts match the built-in Lean profile in the pinned
Vibe 3.1.0 revision and satisfy that revision's strict configuration schema. Its
provider is bound to a loopback-only OpenAI-compatible endpoint, telemetry and
update checks, automatic updates, experiments, connectors, MCP, and subagents
are disabled, and strict configuration validation is enabled. The model
allowlist contains only the frozen Leanstral artifact.
The launch command additionally restricts Vibe's built-in tools to shell, read,
write, edit, and grep operations. File and shell operations are served through
the isolated agent socket and execute inside the one-attempt container.
The fixed qualification prompt requests one `lean --version` tool call so the
same controller path can be checked before scientific execution without
modifying a benchmark task.

[`controller-lock.v1.json`](controller-lock.v1.json) pins these inputs. Validate
them before an attempt:

```bash
python data/formal-verification/vero/controller/validate_controller_lock.py \
  --lock data/formal-verification/vero/controller/controller-lock.v1.json \
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json
```
