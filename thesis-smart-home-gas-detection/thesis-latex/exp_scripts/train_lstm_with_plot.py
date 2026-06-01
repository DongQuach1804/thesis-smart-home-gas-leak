"""Train the LSTM forecaster and emit thesis artefacts.

Outputs:
  thesis-latex/img/exp/lstm_training.png   (loss + accuracy curves)
  thesis-latex/img/exp/lstm_metrics.json   (final test-set metrics)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from processing.ml.lstm.train_forecaster import (
    simulate, make_dataset, build_model, HORIZON, SEQ_LEN,
)


def main() -> None:
    out_img = ROOT / "thesis-latex" / "img" / "exp" / "lstm_training.png"
    out_json = ROOT / "thesis-latex" / "img" / "exp" / "lstm_metrics.json"
    model_path = ROOT / "processing" / "ml" / "lstm" / "gas_forecaster.keras"

    hours = 8.0
    epochs = 15
    batch_size = 128
    seed = 42

    trace = simulate(hours, seed=seed)
    X, y = make_dataset(trace)
    pos = float(y.mean())
    print(f"X={X.shape} y={y.shape} positive={pos:.2%}")

    split = int(len(X) * 0.8)
    Xtr, ytr = X[:split], y[:split]
    Xte, yte = X[split:], y[split:]

    model = build_model()
    history = model.fit(
        Xtr, ytr,
        validation_data=(Xte, yte),
        epochs=epochs,
        batch_size=batch_size,
        class_weight={0: 1.0, 1: max(1.0, (1 - pos) / max(pos, 1e-3))},
        verbose=2,
    )

    model.save(model_path)
    print(f"saved model -> {model_path}")

    # Final test metrics (threshold 0.5)
    y_prob = model.predict(Xte, verbose=0).ravel()
    y_pred = (y_prob >= 0.5).astype(np.float32)
    tp = float(((y_pred == 1) & (yte == 1)).sum())
    fp = float(((y_pred == 1) & (yte == 0)).sum())
    tn = float(((y_pred == 0) & (yte == 0)).sum())
    fn = float(((y_pred == 0) & (yte == 1)).sum())
    accuracy = (tp + tn) / max(1.0, tp + fp + tn + fn)
    precision = tp / max(1.0, tp + fp)
    recall = tp / max(1.0, tp + fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    metrics = {
        "samples_train": int(len(Xtr)),
        "samples_test": int(len(Xte)),
        "positive_rate": round(pos, 4),
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "epochs": epochs,
        "seq_len": SEQ_LEN,
        "horizon": HORIZON,
        "hours": hours,
        "seed": seed,
    }
    out_json.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

    # Plot
    h = history.history
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(h["loss"], label="train")
    axes[0].plot(h["val_loss"], label="validation")
    axes[0].set_xlabel("Epoch"); axes[0].set_ylabel("Binary cross-entropy loss")
    axes[0].set_title("LSTM forecaster: loss")
    axes[0].grid(True, alpha=0.3); axes[0].legend()

    axes[1].plot(h["accuracy"], label="train")
    axes[1].plot(h["val_accuracy"], label="validation")
    axes[1].set_xlabel("Epoch"); axes[1].set_ylabel("Accuracy")
    axes[1].set_title("LSTM forecaster: accuracy")
    axes[1].grid(True, alpha=0.3); axes[1].legend()

    fig.tight_layout()
    fig.savefig(out_img, dpi=120)
    print(f"saved plot -> {out_img}")


if __name__ == "__main__":
    main()
