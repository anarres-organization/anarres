# Local Leanstral inference contract

This directory freezes the model-serving requirements for the Vero starting-policy
probe. The required arguments follow the official Leanstral model card: a
200,000-token context, tensor parallelism across four devices, the
`FLASH_ATTN_MLA` backend, Mistral tool-call and reasoning parsers, and automatic
tool choice. The server binds only to loopback and uses the exact model revision
recorded by the probe protocol.

[`inference-contract.v1.json`](inference-contract.v1.json) intentionally leaves
deployment-host facts unset. Before qualification, record the exact vLLM
version and installation digest, the local model-artifact digest, serving
capacity settings, and readiness receipt. Model resolution may use the network
only before the artifact is sealed; scientific attempts use the resolved local
artifact without external model downloads.

[`qualify_inference_deployment.py`](qualify_inference_deployment.py) verifies
the live process against the frozen flags, checks the loopback endpoint, hashes
the local model artifact, verifies the installed vLLM wheel against its RECORD,
and emits the evidence needed for that transition. It does not edit or qualify
the contract by itself.

Validate the pre-deployment contract with:

```bash
python data/formal-verification/vero/inference/validate_inference_contract.py \
  --contract data/formal-verification/vero/inference/inference-contract.v1.json \
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json \
  --controller-lock data/formal-verification/vero/controller/controller-lock.v1.json
```
