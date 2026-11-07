# Isolated Vibe controller

This directory contains the complete user-level Vibe configuration for the
frozen Vero development probe. The launcher copies only these files into a new
private `VIBE_HOME` for each attempt. It does not load the operator's Vibe home,
credentials, agents, skills, plugins, hooks, MCP servers, or project
configuration.

The Lean agent follows Mistral's published local Leanstral configuration. Its
provider is bound to a loopback-only OpenAI-compatible endpoint, telemetry and
automatic updates are disabled, and strict configuration validation is enabled.
The launch command additionally restricts Vibe's built-in tools to shell, read,
write, edit, and grep operations. File and shell operations are served through
the isolated agent socket and execute inside the one-attempt container.

[`controller-lock.v1.json`](controller-lock.v1.json) pins these inputs. Validate
them before an attempt:

```bash
python data/formal-verification/vero/controller/validate_controller_lock.py \
  --lock data/formal-verification/vero/controller/controller-lock.v1.json \
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json
```
