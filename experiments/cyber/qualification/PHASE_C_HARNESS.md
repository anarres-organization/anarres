# Phase C rollout harness (resolved)

The floor probe needs an agentic harness to drive the warm start through each
task (explore the vulnerable repo, produce a crashing input, submit it for
grading). This records where that harness comes from and the execution plan, so
the measured success reflects the model under a recognized harness rather than an
ad-hoc scaffold.

## Finding

CyberGym does **not** vendor an agent in the dataset mirror we checked out:
`examples/agents/` is a **git submodule** →
`github.com/sunblaze-ucb/cybergym-agent-examples`. That repo provides four
reference harnesses: **Codex, Cybench, EnIGMA, and OpenHands**. The CyberGym
paper's strongest configuration is **OpenHands** (OpenHands + Claude-Sonnet-4,
17.9% without thinking), so OpenHands is the reference harness here.

OpenHands drives tasks via `openhands/run.py`:

```
run.py --model <litellm-model> --data_dir <cybergym data> --task_id <family:id>
       --server http://<host>:<port> --difficulty level1 --max_iter 100
       --timeout 1200
```

It talks to any OpenAI-compatible endpoint, so the open warm start is served
locally with vLLM and `--model openai/<served-name>` + `OPENAI_API_BASE` pointed
at the vLLM server. Each task runs in an OpenHands runtime container; grading goes
to the CyberGym submission server (loopback), on the isolated task network.

## Validity note

The scaffold materially affects measured success, so the floor probe uses the
paper's reference harness (OpenHands) rather than a bespoke loop. The protocol's
decision tree already treats a low/floor result as a valid outcome
(external-target-only / unmeasurable); using the reference harness keeps that
judgment about the model, not a weak scaffold.

## Execution plan (a GPU host with idle GPUs, free Docker root, model verified)

1. Serve the warm start with vLLM on an idle GPU (OpenAI-compatible endpoint);
   smoke-test generation.
2. Set up the OpenHands harness from the submodule; pull its runtime image.
3. Materialize the 48 admitted probe task bundles as the OpenHands `data_dir`,
   and run the CyberGym submission server (loopback) with the firewall.
4. Smoke-test **one** probe task end-to-end (agent → PoC → graded) before
   scaling.
5. Run the frozen two-view G=8 probe: 48 tasks × 16 rollouts, difficulty ≤2.
6. Compute strict success, rho, H, mixed-group fraction, two-view agreement;
   consult `reliability_oc.json` for the abstention rule.
7. Emit one of proceed / external-target-only / unmeasurable per
   `DECISION_TREE.md`. This is never an RL authorization.
