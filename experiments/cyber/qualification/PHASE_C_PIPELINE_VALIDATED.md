# Phase C pipeline validated end-to-end (one task)

The full warm-start-probe pipeline was run end-to-end on one probe task
(`arvo:1348`, an ffmpeg heap-overflow) on skampere1. Every component works; this
records the validated configuration so the scaled 48×16 floor probe is a matter
of running it, not debugging it. No scientific result is claimed from one task;
`execution_authorized` stays `false`.

## What was validated

- **Serving.** vLLM 0.28 (reused from `uv_envs/jra`) serves the digest-verified
  `Nemotron-Terminal-8B` (Qwen3) on one GPU, OpenAI-compatible, with tool calling
  enabled (`--enable-auto-tool-choice --tool-call-parser hermes`).
- **Harness.** OpenHands (from the `cybergym-agent-examples` submodule) builds via
  poetry and runs `openhands.core.main` per task in its runtime container
  (image pulled from `ghcr.io/all-hands-ai/runtime:0.33-nikolaik`, retagged to the
  `docker.all-hands.dev/...` name the config expects).
- **Agent behaviour.** At **temperature 0.7** the agent *acts*: it issues real
  shell commands in the runtime container (`CmdOutputObservation`, exit codes),
  extracts and explores the vulnerable source, and loops to `max_iter`. At
  temperature 0 it instead **degenerated into a repetition loop** and was killed
  by the stuck-detector — so the probe must sample at t>0 (which the two-view
  rollout design requires anyway).
- **Task + grading plumbing.** `run.py`'s `generate_task` builds the agent's
  level-2 bundle from the staged `data_dir`; the CyberGym submission server runs
  loopback with a matching salt; grading uses the ARVO/OSS-Fuzz images.

## Validated configuration (use for the floor probe)

| knob | value |
| --- | --- |
| serve | `vllm serve <model> --served-model-name nemotron-terminal-8b --max-model-len 32768 --gpu-memory-utilization 0.5 --enable-auto-tool-choice --tool-call-parser hermes` |
| model arg | `--model openai/nemotron-terminal-8b --base_url http://127.0.0.1:8713/v1` |
| sampling | `--temperature 0.7 --top_p 0.95` (t>0 mandatory) |
| tool calling | `--native_tool_calling true` |
| difficulty | `level2` (fix/patch/reference hidden; see CONTAINMENT_RESULTS.md) |
| iterations | `--max_iter 100` (paper budget; the 20-step smoke run was too short to submit) |

## Environment gotchas resolved (all on skampere1)

- `run.py` passes a minimal env to the poetry subprocess; it must include `HOME`
  and `PATH` (patched `ENVS`), and `HOME` must point at `/lfs` (poetry config/venv
  live there; the AFS home is read-only → `Permission denied`).
- vLLM 0.28 dropped `--disable-log-requests`; GPUs are 80 GB; the renamed
  `VLLM::EngineCore` worker must be killed explicitly (plain `pkill -f "vllm
  serve"` leaves it holding GPU memory → next launch fails engine init).
- The runtime container writes workspace files as root; clean them via a
  throwaway container, not a host `rm`.

## Remaining for the floor probe

1. Bring up the egress firewall (`python -m cybergym.firewall start`,
   `cybergym-internal` network) so agent rollouts are network-isolated per the
   containment spec; point `--server` at that network's gateway.
2. Run 48 tasks × 16 rollouts (two independent G=8 views) at the config above,
   sharded across the idle GPUs, grading each submission and pruning containers.
3. Compute strict success, ρ, H, mixed-group fraction, and two-view agreement;
   consult `reliability_oc.json` for the abstention rule.
4. Emit one of proceed / external-target-only / unmeasurable per
   `DECISION_TREE.md`. Given an 8B on real CVEs (the paper's frontier best was
   17.9%), a low/floor success rate — and therefore external-target-only or
   unmeasurable — is the expected outcome, which is a valid scientific result.
