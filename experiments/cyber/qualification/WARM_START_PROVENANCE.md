# Warm-start artifact provenance

Date verified: 2026-10-19 (against the Hugging Face public API).

This resolves the artifact-existence half of authorization blocker #1
("record the exact local warm-start artifact digest and verify it matches the
agentic warm start"). The pinned source exists, the pinned revision resolves,
and the download-integrity digests are recorded below. The **local** artifact
digest is still pending: it is computed after the weights are downloaded onto a
container-capable host (see `PHASE_C_PREREQUISITES.md`) and must then be checked
to match the agentic warm start.

## Source

- Repo: `nvidia/Nemotron-Terminal-8B` (public, not gated)
- Pinned revision: `bb1413579351dfada0c203699ea32d2d08f0942c` (resolves, HTTP 200)
- Architecture: `qwen3` (an 8B Qwen3-based terminal / code-agent SFT). This is
  consistent with reusing the agentic terminal warm start for the cyber domain.
- License: `other` (declared on the model card; a license review is still an
  authorization blocker).
- Reference: arXiv:2602.21193 (per the model card tags).

## Download-integrity digests (LFS sha256 at the pinned revision)

| File | Bytes | LFS sha256 |
| --- | ---: | --- |
| model-00001-of-00004.safetensors | 4924333624 | c985abeb57f93a0700e310d9244cd4288b02d8c164e52eecd9a9ba7f6092c97b |
| model-00002-of-00004.safetensors | 3945936288 | 03dfb9976b0d7bd37fa3033d55c912cf30b781aefb547a078898d06fd21137c1 |
| model-00003-of-00004.safetensors | 4944217760 | 1f0f1121c550f32c81fb242fab343050cfcb8d7d79929dcb0b139a3115da8a8d |
| model-00004-of-00004.safetensors | 2567029152 | 3f40e289630e15e658b6df95198ae39e43aba155d51e5ae6b259de3260e70aa5 |
| tokenizer.json | 11422654 | aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4 |

Total safetensors: 16,381,516,824 bytes (~16.4 GB, bf16). These are the upstream
LFS object ids; after download, verifying each file's sha256 against this table
confirms integrity, and the resulting local digest is recorded in the protocol
`starting_policy.local_artifact_digest`.

## Local download + digest verification (DONE, 2026-10-19)

The weights were downloaded at the pinned revision
`bb1413579351dfada0c203699ea32d2d08f0942c` to a GPU-capable host
(`/lfs/skampere1/0/srivatsavad/anarres-cyber-c/models/Nemotron-Terminal-8B`) and
each file's local `sha256sum` was compared to the table above:

| File | Local sha256 matches table |
| --- | :---: |
| model-00001-of-00004.safetensors | ✓ |
| model-00002-of-00004.safetensors | ✓ |
| model-00003-of-00004.safetensors | ✓ |
| model-00004-of-00004.safetensors | ✓ |
| tokenizer.json | ✓ |

All five match, so the local artifact is byte-identical to the pinned upstream
revision; download integrity is confirmed. The weights are not committed to Git.

## Still open on blocker #1

- Confirm the artifact is byte-identical to the *agentic* warm start used by the
  parallel study (`require_exact_match_to_agentic_warm_start`) — needs that
  study's artifact digest to compare against; upstream integrity is now proven.
- Complete the license review (model card declares `other`) before any
  claim-bearing use.
