"""RxnFlow v2.1 reward class for the frozen molecular target adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from rxnflow import RewardFunction
from target_reward_adapter import score_batch


class MolecularTargetReward(RewardFunction):
    """Batch target reward with explicit oracle-failure propagation."""

    objectives = ("docking_qed",)

    def __init__(
        self,
        prepared_target: str,
        timeout_seconds: float = 300.0,
        max_workers: int = 1,
        worker_python: str | None = None,
    ):
        self.prepared_target = Path(prepared_target)
        self.timeout_seconds = timeout_seconds
        self.max_workers = max_workers
        self.worker_python = worker_python

    def score(
        self,
        smiles_list: list[str],
        cond_list: list[dict[str, Any]] | None = None,
    ) -> NDArray[np.float32]:
        if cond_list is not None:
            raise ValueError("MolecularTargetReward uses one frozen target")
        results = score_batch(
            self.prepared_target,
            smiles_list,
            timeout_seconds=self.timeout_seconds,
            max_workers=self.max_workers,
            worker_python=self.worker_python,
        )
        rewards = np.asarray([result["reward"] for result in results], dtype=np.float32)
        return rewards.reshape(-1, 1)
