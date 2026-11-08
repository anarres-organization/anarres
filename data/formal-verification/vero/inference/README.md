# Local Leanstral inference contract

This directory freezes the model-serving requirements for the Vero starting-policy
probe. The model, 200,000-token context, Mistral tool-call and reasoning parsers,
and automatic tool choice follow the official Leanstral model card. The Blackwell
deployment contract uses tensor parallelism across two B200 devices and vLLM's
`FLASHINFER_MLA` backend because the card's `FLASH_ATTN_MLA` backend is not
available for this architecture. It disables multimodal inputs because the probe
is text-only, runs eager execution, and disables optional kernel warmup and
autotuning. The server binds only to loopback and uses the exact model revision
recorded by the probe protocol.

Inference uses the official `vllm/vllm-openai:v0.28.0` image by immutable digest.
The contract also freezes its source revision and the package versions that
define model loading and tokenization. The [vLLM 0.28 release](https://github.com/vllm-project/vllm/releases/tag/v0.28.0)
was tested against the Transformers 5.15 family; later Transformers releases
changed the Pixtral interface used by this Mistral architecture. Qualification
therefore rejects either image drift or changes to the critical package tuple
before a scientific attempt can begin.

[`inference-contract.v1.json`](inference-contract.v1.json) intentionally leaves
deployment-host facts unset. Before qualification, record the local
model-artifact digest, serving capacity settings, and readiness receipt. Model
resolution may use the network only before the artifact is sealed; scientific
attempts use the resolved local artifact without external model downloads.

[`qualify_inference_deployment.py`](qualify_inference_deployment.py) verifies
the live container against the frozen image, source revision, package metadata,
serving flags, GPU assignment, read-only model mount, and loopback endpoint. It
hashes the local model artifact and emits the evidence needed for that
transition. It does not edit or qualify the contract by itself.

Validate the pre-deployment contract with:

```bash
python data/formal-verification/vero/inference/validate_inference_contract.py \
  --contract data/formal-verification/vero/inference/inference-contract.v1.json \
  --protocol data/formal-verification/vero/policy-probe-protocol.v1.json \
  --controller-lock data/formal-verification/vero/controller/controller-lock.v1.json
```
