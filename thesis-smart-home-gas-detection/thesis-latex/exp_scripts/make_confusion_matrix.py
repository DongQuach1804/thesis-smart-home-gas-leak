"""Draw the LSTM confusion matrix from the saved metrics file.

Source: thesis-latex/img/exp/lstm_metrics.json
Output: thesis-latex/img/exp/lstm_confusion_matrix.png

Run:    python thesis-latex/exp_scripts/make_confusion_matrix.py
"""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "img" / "exp" / "lstm_metrics.json"
OUT = ROOT / "img" / "exp" / "lstm_confusion_matrix.png"


def main() -> None:
    with open(METRICS, "r", encoding="utf-8") as f:
        m = json.load(f)
    tp, fp, tn, fn = int(m["tp"]), int(m["fp"]), int(m["tn"]), int(m["fn"])
    total = tp + fp + tn + fn

    # rows = True label, cols = Predicted label
    cm = np.array([[tn, fp],
                   [fn, tp]], dtype=int)

    # Row-normalized (per true class)
    row_sum = cm.sum(axis=1, keepdims=True)
    cm_norm = cm / row_sum

    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0.0, vmax=1.0, aspect="equal")

    # Cell text: normalized value (2 decimals)
    for i in range(2):
        for j in range(2):
            v = cm_norm[i, j]
            text_color = "white" if v > 0.55 else "#1f2d3d"
            ax.text(j, i, f"{v:.2f}",
                    ha="center", va="center",
                    fontsize=20, weight="bold", color=text_color)

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["0", "1"], fontsize=12)
    ax.set_yticklabels(["0", "1"], fontsize=12)
    ax.set_xlabel("Predicted label", fontsize=12)
    ax.set_ylabel("True label", fontsize=12)
    ax.set_title("Normalized confusion matrix", fontsize=13, pad=12)

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=10)

    # Clean spines for the classic sklearn look
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", which="both", length=0)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
