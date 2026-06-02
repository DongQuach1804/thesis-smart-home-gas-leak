"""Evaluate LSTM decision thresholds and export slide-ready figures.

The LSTM emits a probability ``p_critical_5min``. A threshold of 0.5 is
conservative, but gas-leak safety favors recall. This script evaluates several
thresholds on the simulator test split and exports figures for slides.

Run from the project root:

    python slide_model_assets/tune_lstm_threshold.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from processing.ml.lstm.train_forecaster import make_dataset, simulate  # noqa: E402

OUT = ROOT / "slide_model_assets" / "generated"
MODEL_PATH = ROOT / "processing" / "ml" / "lstm" / "gas_forecaster.keras"

BLUE = "#174f91"
MID_BLUE = "#2e7db8"
GREEN = "#4f9954"
RED = "#cf2929"
AMBER = "#efb450"
DARK = "#20252b"
GRID = "#dbe2ea"

THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
SELECTED_THRESHOLD = 0.20


def metrics_at(y_true: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    pred = (scores >= threshold).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum())
    fp = int(((pred == 1) & (y_true == 0)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum())
    fn = int(((pred == 0) & (y_true == 1)).sum())
    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def load_predictions() -> tuple[np.ndarray, np.ndarray]:
    trace = simulate(8.0, seed=42)
    x, y = make_dataset(trace)
    split = int(len(x) * 0.8)
    x_test = x[split:]
    y_test = y[split:].astype(int)
    model = tf.keras.models.load_model(MODEL_PATH)
    scores = model.predict(x_test, verbose=0).ravel()
    return y_test, scores


def plot_threshold_tradeoff(results: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    thresholds = np.array([r["threshold"] for r in results])
    precision = np.array([r["precision"] for r in results])
    recall = np.array([r["recall"] for r in results])
    f1 = np.array([r["f1"] for r in results])

    fig, ax = plt.subplots(figsize=(13.5, 7.2), dpi=150)
    fig.patch.set_facecolor("white")
    ax.plot(thresholds, precision * 100, marker="o", linewidth=2.6,
            color=GREEN, label="Precision")
    ax.plot(thresholds, recall * 100, marker="o", linewidth=2.6,
            color=RED, label="Recall")
    ax.plot(thresholds, f1 * 100, marker="o", linewidth=2.4,
            color=BLUE, label="F1")
    ax.axvline(SELECTED_THRESHOLD, color=AMBER, linewidth=2.0, linestyle="--")

    selected = min(results, key=lambda r: abs(r["threshold"] - SELECTED_THRESHOLD))
    ax.scatter(
        [SELECTED_THRESHOLD],
        [selected["recall"] * 100],
        s=160,
        color=RED,
        edgecolor="white",
        linewidth=1.6,
        zorder=5,
    )
    ax.annotate(
        f"Chọn threshold = {SELECTED_THRESHOLD:.2f}\n"
        f"Recall {selected['recall']:.1%}, Precision {selected['precision']:.1%}",
        xy=(SELECTED_THRESHOLD, selected["recall"] * 100),
        xytext=(0.255, 82),
        arrowprops=dict(arrowstyle="->", color=DARK, lw=1.2),
        fontsize=12,
        color=DARK,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=GRID),
    )

    ax.set_title(
        "Chọn ngưỡng LSTM theo hướng an toàn: ưu tiên recall",
        fontsize=19,
        color=BLUE,
        fontweight="bold",
        pad=20,
    )
    ax.set_xlabel("Decision threshold trên p_critical_5min", fontsize=12)
    ax.set_ylabel("%", fontsize=12)
    ax.set_ylim(0, 105)
    ax.set_xlim(0.08, 0.52)
    ax.grid(axis="y", color=GRID, linewidth=0.9, alpha=0.9)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(labelsize=10.5, colors="#4c5661")
    ax.legend(frameon=False, loc="lower right", fontsize=12)
    fig.text(
        0.5,
        0.04,
        "Bài toán rò rỉ gas phạt bỏ sót nguy hiểm nặng hơn báo nhầm, nên dùng threshold 0.20 thay vì 0.50 khi cần nhãn cảnh báo.",
        ha="center",
        fontsize=12,
        color=BLUE,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0.04, 0.08, 0.98, 0.93])
    fig.savefig(OUT / "13_lstm_threshold_tradeoff.png", bbox_inches="tight")
    plt.close(fig)


def plot_confusion(result: dict) -> None:
    matrix = np.array([[result["tn"], result["fp"]], [result["fn"], result["tp"]]])
    row_sums = matrix.sum(axis=1, keepdims=True)
    pct = matrix / row_sums

    fig, ax = plt.subplots(figsize=(9.8, 7.6), dpi=150)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"LSTM confusion matrix - threshold {result['threshold']:.2f}",
        fontsize=18,
        color=BLUE,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.925,
        f"Accuracy {result['accuracy']:.1%} | Precision {result['precision']:.1%} | "
        f"Recall {result['recall']:.1%} | F1 {result['f1']:.1%}",
        ha="center",
        fontsize=12.5,
        color=BLUE,
        fontweight="bold",
    )
    im = ax.imshow(pct, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks([0, 1], ["Pred 0\nan toàn", "Pred 1\ncảnh báo"],
                  fontsize=12)
    ax.set_yticks([0, 1], ["True 0\nan toàn", "True 1\nnguy cơ"],
                  fontsize=12)

    for i in range(2):
        for j in range(2):
            color = "white" if pct[i, j] > 0.55 else DARK
            ax.text(
                j,
                i,
                f"{matrix[i, j]:,}\n({pct[i, j] * 100:.1f}%)",
                ha="center",
                va="center",
                color=color,
                fontsize=16,
                fontweight="bold",
            )
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks(np.arange(-.5, 2, 1), minor=True)
    ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)
    fig.tight_layout(rect=[0.02, 0.02, 0.95, 0.9])
    fig.savefig(OUT / "14_lstm_confusion_threshold_020.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    y_true, scores = load_predictions()
    results = [metrics_at(y_true, scores, t) for t in THRESHOLDS]
    selected = min(results, key=lambda r: abs(r["threshold"] - SELECTED_THRESHOLD))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "lstm_threshold_metrics.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    plot_threshold_tradeoff(results)
    plot_confusion(selected)
    print(json.dumps(selected, indent=2, ensure_ascii=False))
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
