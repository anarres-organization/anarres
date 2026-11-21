"""STATE-Bench agent extension for the Anarres episodic-memory operator."""

from __future__ import annotations

import os
from pathlib import Path

from agents.anarres_learning_operator import load_artifact, retrieve
from state_bench.agents.state_bench import StateBenchAgent


class AnarresEpisodicMemoryAgent(StateBenchAgent):
    """Expose a frozen Anarres learning artifact through STATE-Bench retrieval."""

    _artifact: dict | None = None

    def retrieve_learnings(self, query: str, top_k: int = 3) -> list[str]:
        artifact_path = os.environ.get("ANARRES_STATE_LEARNINGS_PATH", "").strip()
        if not artifact_path:
            return []
        if self._artifact is None:
            self._artifact = load_artifact(Path(artifact_path))
        return retrieve(self._artifact, query, top_k=top_k)
