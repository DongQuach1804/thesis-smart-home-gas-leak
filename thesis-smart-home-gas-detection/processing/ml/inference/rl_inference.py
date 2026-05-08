"""
RL Inference module — PPO agent for gas leak action recommendation.

The trained PPO model expects observation_space Box(19,) and action_space
Discrete(3):
    action 0 → NORMAL   (no action needed)
    action 1 → WARNING  (alert occupants)
    action 2 → ALERT    (trigger ventilation / alarm)

Observation vector (19 features) — auto-padded/truncated at inference time:
    The live pipeline feeds [gas_ppm_norm, temp_norm, humidity_norm,
    lstm_risk_score] as the first 4 dimensions; remaining dims are zero-padded.
    For best accuracy, extend with a sliding history window matching training.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

ACTION_LABELS = {0: "NORMAL", 1: "WARNING", 2: "ALERT"}


class RLInference:
    """Stable-Baselines3 PPO wrapper for gas leak action recommendation.

    Usage::
        agent  = RLInference(model_path)
        action = agent.choose_action(state)          # state: list of floats
        label  = agent.action_label(action)          # "NORMAL" | "WARNING" | "ALERT"
    """

    def __init__(self, model_path: str | None = None) -> None:
        if model_path is None:
            model_path = os.getenv(
                "RL_MODEL_PATH",
                "/app/ml/rl/ppo_gas_agent.zip",
            )

        path = Path(model_path)
        # Check path BEFORE importing SB3 so the stub test works without install
        if not path.exists():
            raise FileNotFoundError(f"Missing RL model: {model_path}")

        # Lazy imports — stable-baselines3 / torch are heavy
        from stable_baselines3 import PPO  # noqa: PLC0415

        logger.info("Loading PPO RL agent from %s", path)
        self.model = PPO.load(str(path))

        # Auto-detect sizes from the loaded model
        self.obs_size:    int = int(self.model.observation_space.shape[0])
        self.n_actions:   int = int(self.model.action_space.n)
        logger.info(
            "RL agent loaded — obs_size=%d, n_actions=%d",
            self.obs_size, self.n_actions,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def choose_action(self, state: List[float]) -> int:
        """Return the recommended action (int) for a given state vector.

        The input ``state`` is automatically padded with zeros or truncated
        to match the model's expected observation size (``self.obs_size``).
        This allows passing a subset of features during live inference.

        Args:
            state: Feature values in the same order as training features.
                   Typically [gas_ppm_norm, temp_norm, humidity_norm,
                   lstm_risk_score, ...]

        Returns:
            int in [0, n_actions-1]
        """
        obs = np.zeros(self.obs_size, dtype=np.float32)
        n = min(len(state), self.obs_size)
        obs[:n] = np.array(state[:n], dtype=np.float32)

        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    def action_label(self, action: int) -> str:
        """Map integer action to a human-readable label."""
        return ACTION_LABELS.get(action, f"ACTION_{action}")
