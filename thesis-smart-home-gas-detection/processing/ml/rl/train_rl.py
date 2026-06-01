"""
Train a PPO agent on the GasLeakEnv.

Run from repo root::

    python processing/ml/rl/train_rl.py --steps 400000

Saves the policy to ``processing/ml/rl/ppo_gas_agent.zip`` and the
VecNormalize training statistics to ``processing/ml/rl/vecnormalize.pkl``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from processing.ml.rl.gas_env import GasLeakEnv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--episode-seconds", type=int, default=1800)
    parser.add_argument(
        "--monitor-dir",
        type=str,
        default=str(Path(__file__).parent / "ppo_monitor"),
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(Path(__file__).parent / "ppo_gas_agent.zip"),
    )
    parser.add_argument(
        "--vecnormalize-out",
        type=str,
        default=str(Path(__file__).parent / "vecnormalize.pkl"),
    )
    args = parser.parse_args()

    from stable_baselines3 import PPO
    from stable_baselines3.common.env_util import make_vec_env
    from stable_baselines3.common.vec_env import VecNormalize

    env = make_vec_env(
        lambda: GasLeakEnv(episode_seconds=args.episode_seconds),
        n_envs=args.n_envs,
        seed=args.seed,
        monitor_dir=args.monitor_dir,
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
        seed=args.seed,
    )
    model.learn(total_timesteps=args.steps)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    model.save(out)
    print(f"[rl] saved policy -> {out}")
    vec_out = Path(args.vecnormalize_out)
    vec_out.parent.mkdir(parents=True, exist_ok=True)
    env.save(vec_out)
    print(f"[rl] saved VecNormalize stats -> {vec_out}")


if __name__ == "__main__":
    main()
