"""
Inference wrapper around the trained PPO gas-response agent.

If the trained model is missing, falls back to a deterministic rule-based
policy so the pipeline still emits actions while training is in progress.

Action codes (must match ``gas_env.ACTION_NAMES``)::

    0 NO_OP        1 ALERT_USER        2 FAN_ON        3 CLOSE_VALVE
"""
from __future__ import annotations

import logging
import os
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

ACTION_NAMES = ("NO_OP", "ALERT_USER", "FAN_ON", "CLOSE_VALVE")
ACTION_LABELS = {i: name for i, name in enumerate(ACTION_NAMES)}


class _RuleFallback:
    """Conservative rule-based controller used when the PPO model is absent.

    Mirrors the reward shape so behaviour is reasonable: alert early, vent
    if trend is rising, close valve only if predicted_5min is high.
    """

    def __call__(self, obs: np.ndarray) -> int:
        gas_norm, _temp, _hum, slope_norm, p5, fan, valve, _tsa = obs
        gas_ppm = gas_norm * 2000.0
        slope_ppm_per_s = (slope_norm - 0.5) * 20.0

        if gas_ppm > 800 and not valve:
            return 3                           # CLOSE_VALVE
        if p5 > 0.7 and not valve:
            return 3
        if (p5 > 0.4 or slope_ppm_per_s > 1.0) and not fan:
            return 2                           # FAN_ON
        if p5 > 0.3:
            return 1                           # ALERT_USER
        return 0                               # NO_OP


class GasResponseAgent:
    """Encapsulates the per-device controller state and the PPO/fallback policy."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        self._policy = None
        self._fallback = _RuleFallback()
        self._device_state: Dict[str, dict] = {}
        self._gas_hist: Dict[str, Deque[float]] = {}

        path = Path(model_path or os.getenv(
            "RL_MODEL_PATH",
            "/app/ml/rl/ppo_gas_agent.zip",
        ))
        if path.exists():
            try:
                from stable_baselines3 import PPO
                self._policy = PPO.load(str(path))
                logger.info("PPO agent loaded from %s", path)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load PPO model (%s); using rule fallback", exc)
        else:
            logger.warning("PPO model not found at %s — using rule-based fallback", path)

    # ------------------------------------------------------------------

    def _state_for(self, device_id: str) -> dict:
        return self._device_state.setdefault(
            device_id,
            {"fan_on": False, "valve_closed": False, "time_since_action": 0},
        )

    def _slope(self, device_id: str, gas_ppm: float) -> float:
        buf = self._gas_hist.setdefault(device_id, deque(maxlen=30))
        buf.append(gas_ppm)
        if len(buf) < 5:
            return 0.5
        x = np.arange(len(buf), dtype=np.float32)
        slope, _ = np.polyfit(x, np.array(buf, dtype=np.float32), 1)
        return float(np.clip((slope + 10.0) / 20.0, 0.0, 1.0))

    # ------------------------------------------------------------------

    def choose(
        self,
        device_id: str,
        gas_ppm: float,
        temperature_c: float,
        humidity_percent: float,
        p_critical_5min: float,
    ) -> Tuple[int, str]:
        st = self._state_for(device_id)

        obs = np.array([
            min(gas_ppm / 2000.0, 1.0),
            min(temperature_c / 60.0, 1.0),
            min(humidity_percent / 100.0, 1.0),
            self._slope(device_id, gas_ppm),
            float(np.clip(p_critical_5min, 0.0, 1.0)),
            1.0 if st["fan_on"] else 0.0,
            1.0 if st["valve_closed"] else 0.0,
            min(st["time_since_action"] / 300.0, 1.0),
        ], dtype=np.float32)

        if self._policy is not None:
            action, _ = self._policy.predict(obs, deterministic=True)
            action = int(action)
        else:
            action = int(self._fallback(obs))

        # Update internal state for next call
        if action == 2:
            st["fan_on"] = True
            st["time_since_action"] = 0
        elif action == 3:
            st["valve_closed"] = True
            st["time_since_action"] = 0
        elif action == 1:
            st["time_since_action"] = 0
        else:
            st["time_since_action"] += 1

        return action, ACTION_NAMES[action]

    def reset(self, device_id: str) -> None:
        self._device_state.pop(device_id, None)
        self._gas_hist.pop(device_id, None)


# Backwards-compat shim with the older `RLInference` API:
#   - constructor errors (instead of fallback) when the model is missing
#   - exposes `choose_action(state_list)` taking a flat feature vector
class RLInference(GasResponseAgent):
    """Compatibility wrapper exposing the older ``choose_action(state)`` API."""

    def __init__(self, model_path: Optional[str] = None) -> None:
        path = Path(model_path or os.getenv(
            "RL_MODEL_PATH",
            "/app/ml/rl/ppo_gas_agent.zip",
        ))
        if not path.exists():
            raise FileNotFoundError(f"Missing RL model: {path}")
        super().__init__(str(path))
        if self._policy is None:
            raise RuntimeError(f"Failed to load PPO model at {path}")
        self.model = self._policy
        self.obs_size = int(self.model.observation_space.shape[0])
        self.n_actions = int(self.model.action_space.n)

    def choose_action(self, state: List[float]) -> int:
        obs = np.zeros(self.obs_size, dtype=np.float32)
        n = min(len(state), self.obs_size)
        obs[:n] = np.array(state[:n], dtype=np.float32)
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    def action_label(self, action: int) -> str:
        return ACTION_LABELS.get(action, f"ACTION_{action}")
