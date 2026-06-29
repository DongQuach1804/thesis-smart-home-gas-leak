"""
Custom Gymnasium environment for the gas-leak response problem.

The agent observes the current sensor state plus the forecaster's predicted
risk in 5 minutes, and chooses ONE action per step:

    0  NO_OP        — do nothing
    1  ALERT_USER   — push a notification (cheap, non-physical)
    2  FAN_ON       — start ventilation, accelerates gas decay
    3  CLOSE_VALVE  — stop the leak entirely

Reward shaping
--------------
+10  if action correctly prevents gas from reaching CRITICAL
-50  per timestep where gas >= CRITICAL  (huge penalty for missing a leak)
-2   for ALERT_USER when leak_state == NORMAL    (false positive)
-5   for FAN_ON / CLOSE_VALVE when leak_state == NORMAL (costly false positive)
-0.05 per timestep (light step penalty to encourage decisive action)

The env wraps the same physical world as the simulator so the policy
trains on the exact dynamics that production sees.
"""
from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:  # pragma: no cover
    import gym                                # type: ignore[no-redef]
    from gym import spaces                    # type: ignore[no-redef]

from device.simulator.sensor_simulator import (
    State, World, STEP_FN, _maybe_transition, _seconds_to_critical,
)

ACTION_NAMES = ("NO_OP", "ALERT_USER", "FAN_ON", "CLOSE_VALVE")
NUM_ACTIONS = len(ACTION_NAMES)

CRITICAL_PPM = 1000.0
HORIZON = 300


class GasLeakEnv(gym.Env):
    """Discrete-action environment over the simulator's physical model."""

    metadata = {"render_modes": []}

    def __init__(self, episode_seconds: int = 1800, seed: Optional[int] = None):
        super().__init__()
        self.episode_seconds = episode_seconds
        self._rng = np.random.default_rng(seed)

        # Observation: [gas_norm, temp_norm, hum_norm, slope_norm,
        #               p_critical_5min, fan_on, valve_closed, time_since_action]
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(8,), dtype=np.float32,
        )
        self.action_space = spaces.Discrete(NUM_ACTIONS)

        self.world = World()
        self.t = 0
        self.fan_on = False
        self.valve_closed = False
        self.time_since_action = 0
        self._gas_history: list[float] = []

    # ------------------------------------------------------------------
    # Gym API
    # ------------------------------------------------------------------

    def reset(self, *, seed: Optional[int] = None, options: Any = None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self.world = World()
        self.t = 0
        self.fan_on = False
        self.valve_closed = False
        self.time_since_action = 0
        self._gas_history = []
        return self._observe(p_forecast=0.0), {}

    def step(self, action: int):
        # ── Apply action effects on the world ──────────────────────────
        action_cost = 0.0
        leak_state = self.world.state

        if action == 1:                                       # ALERT_USER
            # Cheap notification — but still costs if user is being spammed
            action_cost = -3.0 if leak_state == State.NORMAL else 0.0
            self.time_since_action = 0
        elif action == 2:                                     # FAN_ON
            if not self.fan_on:
                self.fan_on = True
                # STRONGER penalty so agent learns to wait until p5 is real
                action_cost = -15.0 if leak_state == State.NORMAL else 0.0
            self.time_since_action = 0
        elif action == 3:                                     # CLOSE_VALVE
            if not self.valve_closed:
                self.valve_closed = True
                # Stops the leak: force VENTILATING
                if leak_state in (State.LEAK_SLOW, State.LEAK_FAST):
                    self.world.state = State.VENTILATING
                    self.world.state_age_s = 0.0
                else:
                    action_cost = -25.0       # Closing the gas valve in NORMAL is BAD
            self.time_since_action = 0
        else:                                                 # NO_OP
            self.time_since_action += 1

        # ── Step the world physics ─────────────────────────────────────
        STEP_FN[self.world.state](self.world, 1.0)
        if self.fan_on and self.world.state != State.VENTILATING:
            # Fan accelerates decay even mid-leak (partially mitigates)
            self.world.gas = max(50.0, self.world.gas * 0.985)
        _maybe_transition(self.world, 1.0)
        self.world.state_age_s += 1.0
        self.t += 1
        self._gas_history.append(self.world.gas)

        # ── Reward ─────────────────────────────────────────────────────
        reward = -0.05 + action_cost  # small step cost
        if self.world.gas >= CRITICAL_PPM:
            reward -= 50.0
        # Bonus: if we acted during a leak and it never reached critical
        if action in (2, 3) and leak_state in (State.LEAK_SLOW, State.LEAK_FAST):
            reward += 10.0

        # ── Termination ────────────────────────────────────────────────
        terminated = False
        truncated = self.t >= self.episode_seconds

        # Cheap forecast estimate via slope (training time only)
        p_forecast = self._cheap_forecast()

        return self._observe(p_forecast), float(reward), terminated, truncated, {
            "leak_state": self.world.state.value,
            "gas_ppm": self.world.gas,
            "ttc": _seconds_to_critical(self.world),
        }

    # ------------------------------------------------------------------
    # Observation helpers
    # ------------------------------------------------------------------

    def _cheap_forecast(self) -> float:
        if len(self._gas_history) < 5:
            return 0.0
        n = min(30, len(self._gas_history))
        x = np.arange(n, dtype=np.float32)
        slope, _ = np.polyfit(x, self._gas_history[-n:], 1)
        predicted = self.world.gas + slope * HORIZON
        return float(1.0 / (1.0 + math.exp(-(predicted - CRITICAL_PPM) / 200.0)))

    def _slope(self) -> float:
        if len(self._gas_history) < 5:
            return 0.5
        n = min(30, len(self._gas_history))
        x = np.arange(n, dtype=np.float32)
        slope, _ = np.polyfit(x, self._gas_history[-n:], 1)
        # Map slope (ppm/s) into [0,1]: -10 → 0, 0 → 0.5, +10 → 1
        return float(np.clip((slope + 10.0) / 20.0, 0.0, 1.0))

    def _observe(self, p_forecast: float) -> np.ndarray:
        return np.array([
            min(self.world.gas / 2000.0, 1.0),
            min(self.world.temp / 60.0, 1.0),
            min(self.world.hum / 100.0, 1.0),
            self._slope(),
            float(np.clip(p_forecast, 0.0, 1.0)),
            1.0 if self.fan_on else 0.0,
            1.0 if self.valve_closed else 0.0,
            min(self.time_since_action / 300.0, 1.0),
        ], dtype=np.float32)
