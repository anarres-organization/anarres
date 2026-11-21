"""Run STATE-Bench with one OpenAI-compatible Chat Completions gateway."""

from __future__ import annotations

from clients.anarres_gateway_client import AnarresChatCompletionsClient
from state_bench.scripts import run_batch


def _evaluator_client() -> AnarresChatCompletionsClient:
    return AnarresChatCompletionsClient.evaluator_from_env()


def main() -> None:
    run_batch.build_user_sim_client = _evaluator_client
    run_batch.build_locked_judge_client = _evaluator_client
    run_batch.main()


if __name__ == "__main__":
    main()
