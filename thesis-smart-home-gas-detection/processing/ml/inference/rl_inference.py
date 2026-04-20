from pathlib import Path
import numpy as np
from stable_baselines3 import PPO


class RLInference:
    def __init__(self, model_path: str):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Missing RL model: {model_path}")
        self.model = PPO.load(model_path)

    def choose_action(self, state: list[float]) -> int:
        obs = np.array(state, dtype=np.float32)
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)
