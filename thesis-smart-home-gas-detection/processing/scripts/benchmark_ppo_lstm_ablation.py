"""Train and benchmark true PPO-only against the current LSTM+PPO pipeline.

This script answers the thesis-review question: what happens when PPO no
longer uses the LSTM output at all?

Important distinction:
  * This is NOT the 8-dimensional LSTM+PPO policy with p_critical_5min set to 0.
  * PPO-only is a separate PPO policy trained on a 7-dimensional observation:

        gas, temperature, humidity, slope, fan_on, valve_closed, time_since_action

The current LSTM+PPO policy still uses the deployed 8-dimensional observation:

        gas, temperature, humidity, slope, p_critical_5min, fan_on,
        valve_closed, time_since_action

Outputs:
  * img/exp/ppo_lstm_ablation_results.json
  * img/exp/ppo_lstm_ablation_results.txt
  * img/exp/ppo_lstm_ablation_chart.png
  * img/exp/ppo_lstm_ablation_timeline.png
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Disable stochastic leak transitions before importing the simulator.
os.environ["SIM_LEAK_PROB_PER_MIN"] = "0"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:  # pragma: no cover
    import gym  # type: ignore[no-redef]
    from gym import spaces  # type: ignore[no-redef]

from device.simulator.sensor_simulator import State, World, STEP_FN  # noqa: E402
from processing.ml.inference.forecaster_inference import GasForecaster  # noqa: E402
from processing.ml.inference.rl_inference import GasResponseAgent  # noqa: E402

CRITICAL = 1000.0
EPISODE_SECONDS = 3600
LEAK_TRIGGER_T = 600
LEAK_AUTORESOLVE_AGE = 240
ALARM_GAP_S = 60
ACTION_NAMES = ("NO_OP", "ALERT_USER", "FAN_ON", "CLOSE_VALVE")
CONTROLLERS = ("ppo_only", "lstm_ppo")


class PPOOnlyGasLeakEnv(gym.Env):
    """Gas-leak environment with no LSTM forecast dimension in observation."""

    metadata = {"render_modes": []}

    def __init__(self, episode_seconds: int = 1800, seed: int | None = None):
        super().__init__()
        self.episode_seconds = episode_seconds
        self._rng = np.random.default_rng(seed)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(7,),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(len(ACTION_NAMES))
        self.world = World()
        self.t = 0
        self.fan_on = False
        self.valve_closed = False
        self.time_since_action = 0
        self._gas_history: list[float] = []

    def reset(self, *, seed: int | None = None, options=None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self.world = World()
        self.t = 0
        self.fan_on = False
        self.valve_closed = False
        self.time_since_action = 0
        self._gas_history = []
        return self._observe(), {}

    def step(self, action: int):
        cost = 0.0
        leak_state = self.world.state
        leaking = leak_state in (State.LEAK_SLOW, State.LEAK_FAST)

        if action == 1:
            cost = -3.0 if leak_state == State.NORMAL else 0.0
            self.time_since_action = 0
        elif action == 2:
            if not self.fan_on:
                self.fan_on = True
                if leak_state == State.NORMAL:
                    cost = -15.0
            self.time_since_action = 0
        elif action == 3:
            if not self.valve_closed:
                self.valve_closed = True
                if leaking:
                    self.world.state = State.VENTILATING
                    self.world.state_age_s = 0.0
                else:
                    cost = -25.0
            self.time_since_action = 0
        else:
            self.time_since_action += 1

        STEP_FN[self.world.state](self.world, 1.0)
        if self.fan_on and self.world.state != State.VENTILATING:
            self.world.gas = max(50.0, self.world.gas * 0.985)
        self.world.state_age_s += 1.0
        self.t += 1
        self._gas_history.append(self.world.gas)

        reward = -0.05 + cost
        if self.world.gas >= CRITICAL:
            reward -= 50.0
        if leaking and self.world.gas < CRITICAL:
            reward += 0.3
        if self.world.state == State.NORMAL:
            if self.valve_closed:
                reward -= 0.5
            if self.fan_on:
                reward -= 0.1
        if self.world.state == State.NORMAL and self.world.state_age_s > 20:
            self.valve_closed = False
            self.fan_on = False

        return (
            self._observe(),
            float(reward),
            False,
            self.t >= self.episode_seconds,
            {"leak_state": self.world.state.value, "gas_ppm": self.world.gas},
        )

    def _slope(self) -> float:
        if len(self._gas_history) < 5:
            return 0.5
        n = min(30, len(self._gas_history))
        x = np.arange(n, dtype=np.float32)
        slope, _ = np.polyfit(x, self._gas_history[-n:], 1)
        return float(np.clip((slope + 10.0) / 20.0, 0.0, 1.0))

    def _observe(self) -> np.ndarray:
        return np.array(
            [
                min(self.world.gas / 2000.0, 1.0),
                min(self.world.temp / 60.0, 1.0),
                min(self.world.hum / 100.0, 1.0),
                self._slope(),
                1.0 if self.fan_on else 0.0,
                1.0 if self.valve_closed else 0.0,
                min(self.time_since_action / 300.0, 1.0),
            ],
            dtype=np.float32,
        )


def _transition_slow(world: World, t: int) -> None:
    if t == LEAK_TRIGGER_T and world.state == State.NORMAL:
        world.state = State.LEAK_SLOW
        world.state_age_s = 0.0
        return
    _self_resolve(world)


def _transition_fast(world: World, t: int) -> None:
    if t == LEAK_TRIGGER_T and world.state == State.NORMAL:
        world.state = State.LEAK_FAST
        world.state_age_s = 0.0
        return
    _self_resolve(world)


def _self_resolve(world: World) -> None:
    if world.state in (State.LEAK_SLOW, State.LEAK_FAST):
        if world.state_age_s > LEAK_AUTORESOLVE_AGE:
            world.state = State.VENTILATING
            world.state_age_s = 0.0
    elif world.state == State.VENTILATING:
        if world.gas < 100 and world.state_age_s > 30:
            world.state = State.NORMAL
            world.state_age_s = 0.0


SCENARIOS: dict[str, Callable[[World, int], None]] = {
    "slow": _transition_slow,
    "fast": _transition_fast,
}


@dataclass
class ControllerMemory:
    fan_on: bool = False
    valve_closed: bool = False
    time_since_action: int = 0
    gas_history: deque[float] = field(default_factory=lambda: deque(maxlen=30))

    def slope_norm(self, gas_ppm: float) -> float:
        self.gas_history.append(gas_ppm)
        if len(self.gas_history) < 5:
            return 0.5
        y = np.array(self.gas_history, dtype=np.float32)
        x = np.arange(len(y), dtype=np.float32)
        slope, _ = np.polyfit(x, y, 1)
        return float(np.clip((slope + 10.0) / 20.0, 0.0, 1.0))

    def observe_ppo_only(self, world: World) -> np.ndarray:
        return np.array(
            [
                min(world.gas / 2000.0, 1.0),
                min(world.temp / 60.0, 1.0),
                min(world.hum / 100.0, 1.0),
                self.slope_norm(world.gas),
                1.0 if self.fan_on else 0.0,
                1.0 if self.valve_closed else 0.0,
                min(self.time_since_action / 300.0, 1.0),
            ],
            dtype=np.float32,
        )

    def update_action(self, action: int) -> None:
        if action == 2:
            self.fan_on = True
            self.time_since_action = 0
        elif action == 3:
            self.valve_closed = True
            self.time_since_action = 0
        elif action == 1:
            self.time_since_action = 0
        else:
            self.time_since_action += 1


@dataclass
class RunStats:
    controller: str
    scenario: str
    seed: int
    leaks_total: int = 0
    leaks_oracle_critical: int = 0
    misses: int = 0
    lead_times: list[float] = field(default_factory=list)
    alarm_events: int = 0
    normal_seconds: int = 0
    leak_peak_gas: list[float] = field(default_factory=list)
    reached_critical: int = 0
    first_action: str = "NO_OP"

    def summary(self) -> dict:
        oracle = max(1, self.leaks_oracle_critical)
        peak = float(np.mean(self.leak_peak_gas)) if self.leak_peak_gas else 0.0
        return {
            "controller": self.controller,
            "scenario": self.scenario,
            "seed": self.seed,
            "leaks_total": self.leaks_total,
            "leaks_oracle_critical": self.leaks_oracle_critical,
            "lead_time_s": round(float(np.mean(self.lead_times)), 1)
            if self.lead_times
            else 0.0,
            "miss_rate": round(self.misses / oracle, 3),
            "alarms_per_hour": round(
                self.alarm_events / max(1, self.normal_seconds / 3600.0), 2
            ),
            "mean_peak_gas": round(peak, 1),
            "reached_critical_rate": round(
                self.reached_critical / max(1, self.leaks_total), 3
            ),
            "first_action": self.first_action,
        }


def find_thesis_exp_dir() -> Path:
    candidates = [p for p in ROOT.iterdir() if p.is_dir() and (p / "main.tex").exists()]
    if candidates:
        return candidates[0] / "img" / "exp"
    return ROOT / "thesis-latex" / "img" / "exp"


def train_ppo_only(model_path: Path, steps: int, seed: int, force: bool) -> None:
    if model_path.exists() and not force:
        print(f"[ppo-only] using existing model -> {model_path}")
        return

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import VecNormalize

    print(f"[ppo-only] training true 7-input PPO for {steps} steps ...")
    env = make_vec_env(
        lambda: PPOOnlyGasLeakEnv(episode_seconds=1800),
        n_envs=4,
        seed=seed,
        monitor_dir=str(model_path.parent / "ppo_only_monitor"),
    )
    env = VecNormalize(env, norm_obs=False, norm_reward=True, clip_reward=10.0)
    model = PPO(
        "MlpPolicy",
        env,
        n_steps=512,
        batch_size=128,
        gae_lambda=0.95,
        gamma=0.99,
        learning_rate=3e-4,
        ent_coef=0.01,
        verbose=1,
        seed=seed,
    )
    model.learn(total_timesteps=steps)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(model_path)
    env.save(model_path.with_name("ppo_only_vecnormalize.pkl"))
    print(f"[ppo-only] saved model -> {model_path}")


def run_oracle(scenario: str, seed: int) -> dict[int, dict]:
    random.seed(seed)
    np.random.seed(seed)
    transition = SCENARIOS[scenario]
    world = World()
    leaks: dict[int, dict] = {}
    leak_id = -1
    in_leak = False

    for t in range(EPISODE_SECONDS):
        STEP_FN[world.state](world, 1.0)
        transition(world, t)
        world.state_age_s += 1.0

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            leak_id += 1
            leaks[leak_id] = {"start_t": t, "natural_critical_t": None}
            in_leak = True
        elif in_leak:
            if world.gas >= CRITICAL and leaks[leak_id]["natural_critical_t"] is None:
                leaks[leak_id]["natural_critical_t"] = t
            if not leaking:
                in_leak = False
    return leaks


def run_controller(
    controller: str,
    scenario: str,
    seed: int,
    oracle: dict[int, dict],
    forecaster: GasForecaster,
    lstm_ppo_agent: GasResponseAgent,
    ppo_only_policy,
    capture: bool = False,
) -> tuple[dict, list[dict]]:
    random.seed(seed)
    np.random.seed(seed)

    transition = SCENARIOS[scenario]
    stats = RunStats(controller=controller, scenario=scenario, seed=seed)
    world = World()
    memory = ControllerMemory()
    device_id = f"ablation-{controller}-{scenario}-{seed}"
    lstm_ppo_agent.reset(device_id)

    in_leak = False
    leak_id = -1
    leak_first_action_t = -1
    leak_peak = 0.0
    leak_reached_critical = False
    last_alarm_t = -1_000_000
    last_p5 = 0.0
    trace: list[dict] = []

    for t in range(EPISODE_SECONDS):
        STEP_FN[world.state](world, 1.0)
        if memory.fan_on and world.state != State.VENTILATING:
            world.gas = max(50.0, world.gas * 0.985)
        transition(world, t)
        world.state_age_s += 1.0

        if world.state == State.NORMAL and world.state_age_s > 20:
            memory.fan_on = False
            memory.valve_closed = False

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            in_leak = True
            leak_id += 1
            stats.leaks_total += 1
            leak_first_action_t = -1
            leak_peak = world.gas
            leak_reached_critical = False
            if leak_id in oracle and oracle[leak_id]["natural_critical_t"] is not None:
                stats.leaks_oracle_critical += 1
        elif in_leak:
            leak_peak = max(leak_peak, world.gas)
            leak_reached_critical = leak_reached_critical or world.gas >= CRITICAL
            if not leaking:
                stats.leak_peak_gas.append(leak_peak)
                if leak_reached_critical:
                    stats.reached_critical += 1
                if (
                    leak_id in oracle
                    and oracle[leak_id]["natural_critical_t"] is not None
                    and leak_first_action_t < 0
                ):
                    stats.misses += 1
                in_leak = False
        else:
            stats.normal_seconds += 1

        if controller == "ppo_only":
            obs = memory.observe_ppo_only(world)
            action, _ = ppo_only_policy.predict(obs, deterministic=True)
            action = int(action)
            action_label = ACTION_NAMES[action]
            p5_for_trace = math.nan
        elif controller == "lstm_ppo":
            if t % 5 == 0:
                last_p5 = forecaster.predict(device_id, world.gas, world.temp, world.hum)
            action, action_label = lstm_ppo_agent.choose(
                device_id, world.gas, world.temp, world.hum, last_p5
            )
            p5_for_trace = last_p5
        else:
            raise ValueError(controller)

        memory.update_action(action)

        if capture and t % 2 == 0:
            trace.append(
                {
                    "t": t,
                    "gas": round(float(world.gas), 2),
                    "p5": None if math.isnan(p5_for_trace) else round(float(p5_for_trace), 4),
                    "action": int(action),
                    "action_label": action_label,
                    "state": world.state.value,
                }
            )

        if action == 0:
            continue

        if in_leak and leak_first_action_t < 0:
            leak_first_action_t = t
            stats.first_action = action_label
            natural_t = oracle.get(leak_id, {}).get("natural_critical_t")
            if natural_t is not None:
                lead = natural_t - t
                if lead >= 0:
                    stats.lead_times.append(float(lead))
                else:
                    stats.misses += 1

        if not in_leak and (t - last_alarm_t) > ALARM_GAP_S:
            stats.alarm_events += 1
            last_alarm_t = t
        elif not in_leak:
            last_alarm_t = t

        if action == 3 and in_leak:
            world.state = State.VENTILATING
            world.state_age_s = 0.0

    if in_leak:
        stats.leak_peak_gas.append(leak_peak)
        if leak_reached_critical:
            stats.reached_critical += 1

    return stats.summary(), trace


def aggregate(runs: list[dict]) -> dict:
    keys = ("lead_time_s", "miss_rate", "alarms_per_hour", "mean_peak_gas")
    out = {
        "controller": runs[0]["controller"],
        "scenario": runs[0]["scenario"],
        "first_action": runs[0]["first_action"],
    }
    for key in keys:
        vals = [r[key] for r in runs]
        out[f"{key}_mean"] = round(float(np.mean(vals)), 2)
        out[f"{key}_std"] = round(float(np.std(vals)), 2)
    out["reached_critical_rate_mean"] = round(
        float(np.mean([r["reached_critical_rate"] for r in runs])), 2
    )
    return out


def draw_summary_chart(aggregated: list[dict], out_path: Path) -> None:
    labels = {
        "ppo_only": "PPO only",
        "lstm_ppo": "LSTM + PPO",
        "slow": "Slow leak",
        "fast": "Fast leak",
    }
    colors = {"ppo_only": "#d97941", "lstm_ppo": "#2f78b7"}
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.2))
    metrics = [
        ("lead_time_s_mean", "Lead time (s)", "{:.1f}"),
        ("mean_peak_gas_mean", "Peak gas (ppm)", "{:.0f}"),
        ("alarms_per_hour_mean", "False actions / hour", "{:.1f}"),
    ]
    scenarios = list(SCENARIOS)
    x = np.arange(len(scenarios))
    width = 0.36

    legend_handles = []
    legend_labels = []
    for ax, (metric, title, fmt) in zip(axes, metrics):
        all_vals: list[float] = []
        for idx, ctrl in enumerate(CONTROLLERS):
            vals = [
                next(
                    r[metric]
                    for r in aggregated
                    if r["scenario"] == scenario and r["controller"] == ctrl
                )
                for scenario in scenarios
            ]
            all_vals.extend(vals)
            bars = ax.bar(
                x + (idx - 0.5) * width,
                vals,
                width,
                label=labels[ctrl],
                color=colors[ctrl],
                edgecolor="#263238",
                linewidth=0.7,
            )
            if len(legend_handles) < len(CONTROLLERS):
                legend_handles.append(bars[0])
                legend_labels.append(labels[ctrl])
            for bar, value in zip(bars, vals):
                label_y = bar.get_height()
                if value == 0:
                    label_y = 0
                ax.annotate(
                    fmt.format(value),
                    xy=(bar.get_x() + bar.get_width() / 2, label_y),
                    xytext=(0, 5 if value > 0 else 4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color="#263238",
                )
        ymax = max(all_vals + [1.0])
        if metric == "mean_peak_gas_mean":
            ymax = max(ymax, CRITICAL)
        ax.set_ylim(0, ymax * 1.22)
        ax.set_title(title, fontsize=12, pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels([labels[s] for s in scenarios], fontsize=10)
        ax.grid(axis="y", alpha=0.22)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if metric == "mean_peak_gas_mean":
            ax.axhline(
                CRITICAL,
                color="#b71c1c",
                lw=1.0,
                ls="--",
                alpha=0.55,
                label="Critical threshold",
            )
            ax.text(
                1.03,
                CRITICAL,
                "1000 ppm",
                transform=ax.get_yaxis_transform(),
                ha="left",
                va="center",
                fontsize=8,
                color="#8b1a1a",
            )

    fig.legend(
        legend_handles,
        legend_labels,
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.94),
        fontsize=11,
    )
    fig.suptitle("True PPO-only vs LSTM+PPO", fontsize=15, weight="bold", y=0.995)
    fig.subplots_adjust(left=0.06, right=0.97, bottom=0.13, top=0.78, wspace=0.28)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def draw_timeline(trace_by_controller: dict[str, list[dict]], out_path: Path) -> None:
    labels = {"ppo_only": "PPO only (7 inputs)", "lstm_ppo": "LSTM + PPO (8 inputs)"}
    colors = {"ppo_only": "#d97941", "lstm_ppo": "#2f78b7"}
    fig, axes = plt.subplots(2, 1, figsize=(14.5, 7.4), sharex=True)
    window_start = LEAK_TRIGGER_T - 80
    window_end = LEAK_TRIGGER_T + 380

    for ax, ctrl in zip(axes, CONTROLLERS):
        trace = trace_by_controller[ctrl]
        t = np.array([p["t"] for p in trace], dtype=float)
        gas = np.array([p["gas"] for p in trace], dtype=float)
        actions = np.array([p["action"] for p in trace], dtype=int)
        visible = (t >= window_start) & (t <= window_end)
        t_visible = t[visible]
        gas_visible = gas[visible]
        actions_visible = actions[visible]

        ax.plot(t_visible, gas_visible, color=colors[ctrl], lw=2.2, label="gas_ppm")
        if ctrl == "lstm_ppo":
            p5 = np.array([p["p5"] or 0.0 for p in trace], dtype=float) * CRITICAL
            ax.plot(
                t_visible,
                p5[visible],
                color="#6a4c93",
                lw=1.7,
                ls="--",
                label="p_critical_5min x1000",
            )
        ax.axhline(CRITICAL, color="#b71c1c", lw=1.0, ls="--", label="critical")
        ax.axvline(LEAK_TRIGGER_T, color="#555555", lw=1.0, ls=":", label="leak starts")

        action_points = actions_visible > 0
        ax.scatter(
            t_visible[action_points],
            gas_visible[action_points],
            s=18,
            color="#111111",
            marker="o",
            alpha=0.58,
            label="PPO action",
            zorder=5,
        )
        ax.set_title(labels[ctrl], fontsize=12, pad=10)
        ax.set_ylabel("ppm")
        ax.set_xlim(window_start, window_end)
        ax.set_ylim(0, max(1200, float(np.max(gas_visible)) + 160))
        ax.grid(alpha=0.22)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(loc="upper right", fontsize=8, frameon=True, framealpha=0.92)

    axes[-1].set_xlabel("Simulation time (s)")
    fig.suptitle(
        "TC-Fast timeline: true PPO-only versus LSTM+PPO",
        fontsize=15,
        weight="bold",
        y=0.985,
    )
    fig.subplots_adjust(left=0.07, right=0.97, bottom=0.09, top=0.88, hspace=0.34)
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def write_text_report(aggregated: list[dict], out_path: Path) -> None:
    lines = [
        "True PPO-only vs LSTM+PPO ablation",
        "=" * 78,
        f"{'Scenario':<10} {'Controller':<10} {'Lead(s)':>10} {'Miss%':>10} "
        f"{'Alarm/h':>10} {'Peak(ppm)':>12} {'ReachCrit':>10}",
        "-" * 78,
    ]
    for scenario in SCENARIOS:
        for ctrl in CONTROLLERS:
            row = next(
                r
                for r in aggregated
                if r["scenario"] == scenario and r["controller"] == ctrl
            )
            lines.append(
                f"{scenario:<10} {ctrl:<10} "
                f"{row['lead_time_s_mean']:>6.1f}+/-{row['lead_time_s_std']:<4.1f} "
                f"{row['miss_rate_mean'] * 100:>6.1f}% "
                f"{row['alarms_per_hour_mean']:>10.2f} "
                f"{row['mean_peak_gas_mean']:>12.1f} "
                f"{row['reached_critical_rate_mean'] * 100:>9.1f}%"
            )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--train-steps", type=int, default=400_000)
    parser.add_argument("--train-seed", type=int, default=42)
    parser.add_argument("--force-train", action="store_true")
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(find_thesis_exp_dir()),
        help="Directory for JSON/TXT/PNG outputs.",
    )
    parser.add_argument(
        "--forecast-model",
        type=str,
        default=str(ROOT / "processing" / "ml" / "lstm" / "gas_forecaster.keras"),
    )
    parser.add_argument(
        "--lstm-ppo-model",
        type=str,
        default=str(ROOT / "processing" / "ml" / "rl" / "ppo_gas_agent.zip"),
    )
    parser.add_argument(
        "--ppo-only-model",
        type=str,
        default=str(ROOT / "processing" / "ml" / "rl" / "ppo_only_gas_agent.zip"),
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ppo_only_model_path = Path(args.ppo_only_model)
    train_ppo_only(
        ppo_only_model_path,
        steps=args.train_steps,
        seed=args.train_seed,
        force=args.force_train,
    )

    from stable_baselines3 import PPO

    ppo_only_policy = PPO.load(str(ppo_only_model_path))
    forecaster = GasForecaster(args.forecast_model)
    lstm_ppo_agent = GasResponseAgent(args.lstm_ppo_model)
    if lstm_ppo_agent._policy is None:  # noqa: SLF001
        raise RuntimeError("LSTM+PPO model did not load; refusing to benchmark fallback.")

    runs: list[dict] = []
    timeline: dict[str, list[dict]] = {}

    for scenario in SCENARIOS:
        for idx in range(args.seeds):
            seed = args.seed_start + idx
            oracle = run_oracle(scenario, seed)
            for ctrl in CONTROLLERS:
                capture = scenario == "fast" and seed == args.seed_start
                summary, trace = run_controller(
                    ctrl,
                    scenario,
                    seed,
                    oracle,
                    forecaster,
                    lstm_ppo_agent,
                    ppo_only_policy,
                    capture=capture,
                )
                runs.append(summary)
                if capture:
                    timeline[ctrl] = trace

    aggregated: list[dict] = []
    for scenario in SCENARIOS:
        for ctrl in CONTROLLERS:
            selected = [
                r for r in runs if r["scenario"] == scenario and r["controller"] == ctrl
            ]
            aggregated.append(aggregate(selected))

    payload = {
        "meta": {
            "method": (
                "ppo_only is a separate 7-input PPO policy; lstm_ppo is the "
                "current 8-input policy using GasForecaster p_critical_5min."
            ),
            "seeds": list(range(args.seed_start, args.seed_start + args.seeds)),
            "train_steps": args.train_steps,
            "forecast_model": str(Path(args.forecast_model).resolve()),
            "lstm_ppo_model": str(Path(args.lstm_ppo_model).resolve()),
            "ppo_only_model": str(ppo_only_model_path.resolve()),
        },
        "runs": runs,
        "aggregated": aggregated,
        "timeline_fast_seed": timeline,
    }
    (out_dir / "ppo_lstm_ablation_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    write_text_report(aggregated, out_dir / "ppo_lstm_ablation_results.txt")
    draw_summary_chart(aggregated, out_dir / "ppo_lstm_ablation_chart.png")
    draw_timeline(timeline, out_dir / "ppo_lstm_ablation_timeline.png")

    print(f"Saved -> {out_dir / 'ppo_lstm_ablation_results.json'}")
    print(f"Saved -> {out_dir / 'ppo_lstm_ablation_chart.png'}")
    print(f"Saved -> {out_dir / 'ppo_lstm_ablation_timeline.png'}")
    print()
    print((out_dir / "ppo_lstm_ablation_results.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
