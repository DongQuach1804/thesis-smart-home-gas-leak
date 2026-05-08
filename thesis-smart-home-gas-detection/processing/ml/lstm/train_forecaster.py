"""
Train the gas-leak FORECASTING LSTM.

Generates a long synthetic trace from the simulator's physical state machine,
then builds supervised pairs::

    X[i] = window of 60 consecutive (gas, temp, humidity) samples ending at t
    y[i] = 1 if max gas in (t, t + HORIZON] > CRITICAL else 0

Trains a small Keras model and saves it to
``processing/ml/lstm/gas_forecaster.keras``.

Run from the repo root::

    python processing/ml/lstm/train_forecaster.py --hours 4 --epochs 20
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np

# Make ``device.simulator`` importable from anywhere
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from device.simulator.sensor_simulator import (   # noqa: E402
    World, STEP_FN, _maybe_transition,
)

SEQ_LEN = 60          # samples (= seconds at 1 Hz)
HORIZON = 300         # forecasting horizon in seconds
CRITICAL = 1000.0


def simulate(hours: float, seed: int = 42) -> np.ndarray:
    """Run the simulator deterministically and return an array of
    shape (T, 4): gas, temp, humidity, leak_state_int.
    """
    import random
    random.seed(seed)
    np.random.seed(seed)

    n = int(hours * 3600)
    out = np.zeros((n, 4), dtype=np.float32)
    w = World()
    state_to_int = {"NORMAL": 0, "LEAK_SLOW": 1, "LEAK_FAST": 2, "VENTILATING": 3}

    for t in range(n):
        STEP_FN[w.state](w, 1.0)
        _maybe_transition(w, 1.0)
        w.state_age_s += 1.0
        out[t] = (w.gas, w.temp, w.hum, state_to_int[w.state.value])

    return out


def make_dataset(trace: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build (X, y) for binary forecasting.

    X is normalised to [0, 1] using the same bounds as inference.
    """
    bounds = np.array([2000.0, 60.0, 100.0], dtype=np.float32)

    n = len(trace)
    last = n - HORIZON - 1
    if last <= SEQ_LEN:
        raise ValueError("Trace too short — increase --hours.")

    n_samples = last - SEQ_LEN
    X = np.zeros((n_samples, SEQ_LEN, 3), dtype=np.float32)
    y = np.zeros((n_samples,), dtype=np.float32)

    gas = trace[:, 0]
    feats = trace[:, :3] / bounds

    for i in range(n_samples):
        end = SEQ_LEN + i
        X[i] = feats[i:end]
        future_max = gas[end + 1: end + 1 + HORIZON].max()
        y[i] = 1.0 if future_max > CRITICAL else 0.0

    return X, y


def build_model() -> "tf.keras.Model":  # noqa: F821
    import tensorflow as tf
    inp = tf.keras.layers.Input(shape=(SEQ_LEN, 3))
    x = tf.keras.layers.LSTM(32, return_sequences=False)(inp)
    x = tf.keras.layers.Dropout(0.2)(x)
    x = tf.keras.layers.Dense(16, activation="relu")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid")(x)
    model = tf.keras.Model(inp, out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="binary_crossentropy",
        metrics=["accuracy", tf.keras.metrics.Precision(name="precision"),
                 tf.keras.metrics.Recall(name="recall")],
    )
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=4.0,
                        help="Hours of simulated data to generate")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str,
                        default=str(Path(__file__).parent / "gas_forecaster.keras"))
    args = parser.parse_args()

    print(f"[forecaster] simulating {args.hours} h of data...")
    trace = simulate(args.hours, seed=args.seed)
    print(f"[forecaster] trace shape={trace.shape}, "
          f"leak frac={(trace[:,3] > 0).mean():.2%}")

    print("[forecaster] building dataset...")
    X, y = make_dataset(trace)
    pos = float(y.mean())
    print(f"[forecaster] X={X.shape}  y={y.shape}  positive={pos:.2%}")

    if pos < 0.01 or pos > 0.99:
        print("[forecaster] WARNING: class imbalance is extreme — "
              "consider increasing SIM_LEAK_PROB_PER_MIN or --hours.")

    # 80/20 chronological split (no shuffle — leak events are temporal)
    split = int(len(X) * 0.8)
    Xtr, ytr = X[:split], y[:split]
    Xte, yte = X[split:], y[split:]

    model = build_model()
    model.summary()
    model.fit(
        Xtr, ytr,
        validation_data=(Xte, yte),
        epochs=args.epochs,
        batch_size=args.batch_size,
        class_weight={0: 1.0, 1: max(1.0, (1 - pos) / max(pos, 1e-3))},
        verbose=2,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(out_path)
    print(f"[forecaster] saved model -> {out_path}")


if __name__ == "__main__":
    main()
