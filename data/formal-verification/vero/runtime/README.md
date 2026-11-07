# Vero task runtime

This directory defines the model-facing runtime for the frozen Vero development
probe. The image contains Lean 4.29.1, Python 3, and bounded shell utilities. It
does not contain Vero's benchmark tree, reference solutions, qualification or
prospective repositories, model credentials, or the host grader.

The Dockerfile pins the Ubuntu amd64 manifest and verifies the official elan
v4.2.3 release asset before installing the exact Lean toolchain used by all four
development repositories. The final built-image digest remains pending until
the image is built on the deployment host. Record that digest in
[`runtime-lock.v1.json`](runtime-lock.v1.json), then run the complete containment
contract before a model attempt.

```bash
docker build \
  --file data/formal-verification/vero/runtime/Dockerfile \
  --tag anarres-vero-runtime:qualification \
  data/formal-verification/vero/runtime
```

The tag is only a local build handle. Scientific runs must pass the resulting
immutable `sha256` image ID or repository digest to `serve_vibe_sandbox.py`.

Validate the pre-build lock with:

```bash
python data/formal-verification/vero/runtime/validate_runtime_lock.py \
  --lock data/formal-verification/vero/runtime/runtime-lock.v1.json \
  --panel data/formal-verification/vero/development-lifecycle-panel-v2.json \
  --source-pin data/formal-verification/vero/source-pin.json
```
