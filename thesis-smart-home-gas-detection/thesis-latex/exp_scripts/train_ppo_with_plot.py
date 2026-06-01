"""Train PPO with Monitor wrapping so we can plot the learning curve.

Outputs:
  thesis-latex/img/exp/ppo_reward.png
  thesis-latex/img/exp/ppo_progress.csv
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "thesis-latex" / "img" / "exp"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = OUT_DIR / "ppo_monitor_logs"
LOG_DIR.mkdir(exist_ok=True)


def main() -> None:
    from processing.ml.rl.gas_env import GasLeakEnv
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.monitor import load_results
    from stable_baselines3.common.results_plotter import ts2xy

    n_envs = 4
    steps = 200_000
    seed = 42

    env = make_vec_env(
        lambda: GasLeakEnv(episode_seconds=1800),
        n_envs=n_envs,
        seed=seed,
        monitor_dir=str(LOG_DIR),
    )

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

    out_model = ROOT / "processing" / "ml" / "rl" / "ppo_gas_agent.zip"
    model.save(out_model)
    print(f"saved policy -> {out_model}")

    # Load monitor logs and plot
    results = load_results(str(LOG_DIR))
    x, y = ts2xy(results, "timesteps")
    if len(x) == 0:
        print("no monitor data; skipping plot")
        return

    # Moving average for smoothness
    window = max(1, len(y) // 30)
    if window > 1:
        y_smooth = np.convolve(y, np.ones(window) / window, mode="valid")
        x_smooth = x[window - 1:]
    else:
        y_smooth, x_smooth = y, x

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(x, y, alpha=0.25, label="episode reward")
    ax.plot(x_smooth, y_smooth, color="C0", label=f"moving avg (k={window})")
    ax.set_xlabel("Training timesteps")
    ax.set_ylabel("Episode reward")
    ax.set_title("PPO learning curve on GasLeakEnv")
    ax.grid(True, alpha=0.3); ax.legend()
    fig.tight_layout()
    out_img = OUT_DIR / "ppo_reward.png"
    fig.savefig(out_img, dpi=120)
    print(f"saved plot -> {out_img}")

    import pandas as pd
    pd.DataFrame({"timesteps": x, "ep_reward": y}).to_csv(
        OUT_DIR / "ppo_progress.csv", index=False
    )


if __name__ == "__main__":
    main()
