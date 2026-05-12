"""Measure end-to-end inference latency for the LSTM forecaster and PPO RL.

We benchmark only the components we can run locally without spinning up the
whole Docker stack (Kafka/Spark/Influx). Pipeline-network components are
estimated from broker docs.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "FORECAST_MODEL_PATH",
    str(ROOT / "processing" / "ml" / "lstm" / "gas_forecaster.keras"),
)
os.environ.setdefault(
    "RL_MODEL_PATH",
    str(ROOT / "processing" / "ml" / "rl" / "ppo_gas_agent.zip"),
)

from processing.ml.inference.forecaster_inference import GasForecaster
from processing.ml.inference.rl_inference import GasResponseAgent


def percentile(xs, p):
    return float(np.percentile(xs, p))


def main() -> None:
    forecaster = GasForecaster()
    agent = GasResponseAgent()

    # Warm-up the buffer to full window
    rng = np.random.default_rng(0)
    for i in range(120):
        gas = 60.0 + rng.normal(0, 5)
        forecaster.predict("bench", gas, 28.0, 60.0)

    n = 200
    f_times = []
    for _ in range(n):
        gas = 60.0 + rng.normal(0, 5)
        t0 = time.perf_counter()
        forecaster.predict("bench", gas, 28.0, 60.0)
        f_times.append((time.perf_counter() - t0) * 1000.0)

    r_times = []
    for _ in range(n):
        gas = 60.0 + rng.normal(0, 5)
        p5 = float(rng.uniform(0, 1))
        t0 = time.perf_counter()
        agent.choose("bench", gas, 28.0, 60.0, p5)
        r_times.append((time.perf_counter() - t0) * 1000.0)

    summary = {
        "forecaster_ms": {
            "mean": round(statistics.mean(f_times), 3),
            "median": round(statistics.median(f_times), 3),
            "p95": round(percentile(f_times, 95), 3),
            "p99": round(percentile(f_times, 99), 3),
            "n": n,
        },
        "rl_choose_ms": {
            "mean": round(statistics.mean(r_times), 3),
            "median": round(statistics.median(r_times), 3),
            "p95": round(percentile(r_times, 95), 3),
            "p99": round(percentile(r_times, 99), 3),
            "n": n,
        },
    }
    print(json.dumps(summary, indent=2))
    out = ROOT / "thesis-latex" / "img" / "exp" / "latency_results.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
