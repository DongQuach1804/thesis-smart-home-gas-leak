"""Block diagram of the LSTM forecaster architecture.

Layers (matches processing/ml/forecaster.py):
  Input (60, 3)
   -> LSTM(32, return_sequences=False)
   -> Dropout(0.2)
   -> Dense(16, relu)
   -> Dense(1, sigmoid)  -> p_{5min}

Output: thesis-latex/img/lstm_arch.png
Run:    python thesis-latex/exp_scripts/make_lstm_arch_figure.py
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "lstm_arch.png"


def block(ax, x, y, w, h, title, sub, fill, border):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.18,rounding_size=0.20",
        linewidth=1.8, edgecolor=border, facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h * 0.66, title,
            ha="center", va="center", fontsize=13, weight="bold",
            color="#1f2d3d")
    ax.text(x + w / 2, y + h * 0.30, sub,
            ha="center", va="center", fontsize=10.5, color="#445063")


def arrow(ax, x, y_top, y_bot, label):
    a = FancyArrowPatch(
        (x, y_top), (x, y_bot),
        arrowstyle="-|>", mutation_scale=18, linewidth=1.8,
        color="#34495e",
    )
    ax.add_patch(a)
    ax.text(x + 0.35, (y_top + y_bot) / 2,
            label, ha="left", va="center", fontsize=10,
            color="#34495e",
            bbox=dict(boxstyle="round,pad=0.22",
                      facecolor="white", edgecolor="#d0d0d0",
                      linewidth=0.6))


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(8.5, 12.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 17)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(5.0, 16.3,
            "Kiến trúc LSTM Forecaster ($\\sim$5,000 tham số)",
            ha="center", va="center", fontsize=15, weight="bold",
            color="#1f2d3d")

    in_fill, in_b   = "#fef3e6", "#e8a25b"
    lstm_fill, lstm_b = "#e7eef8", "#4a6fa5"
    drop_fill, drop_b = "#f0e7f7", "#7e3b8e"
    dense_fill, dense_b = "#e6f4ea", "#5ba26c"
    out_fill, out_b   = "#fae7e7", "#b35b5b"

    # Box width: 6.4, centered at x=5.0 => x_left = 1.8
    bw, bx = 6.4, 1.8
    block(ax, bx, 13.7, bw, 1.5,
          "Input layer",
          "shape=(60, 3) — 60 bước $\\times$ (gas, T, H), chuẩn hoá $[0,1]$",
          in_fill, in_b)

    block(ax, bx, 11.0, bw, 1.6,
          "LSTM (32 đơn vị)",
          "return_sequences=False  ·  $\\approx 4{,}608$ tham số",
          lstm_fill, lstm_b)

    block(ax, bx, 8.7, bw, 1.3,
          "Dropout (rate = 0,2)",
          "chỉ hoạt động khi training",
          drop_fill, drop_b)

    block(ax, bx, 6.2, bw, 1.5,
          "Dense (16, ReLU)",
          "fully connected  ·  $32 \\times 16 + 16 = 528$ tham số",
          dense_fill, dense_b)

    block(ax, bx, 3.8, bw, 1.4,
          "Dense (1, Sigmoid)",
          "$16 \\times 1 + 1 = 17$ tham số",
          out_fill, out_b)

    block(ax, bx, 1.4, bw, 1.4,
          "Output  $\\hat{y} = p_{5\\min} \\in [0,1]$",
          "ngưỡng quyết định 0,5 (có thể hạ về 0,35 -- xem §4.2)",
          out_fill, out_b)

    # Arrows (gap of ~0.4 between blocks)
    arrow(ax, 5.0, 13.7, 12.6, "tensor (B, 60, 3)")
    arrow(ax, 5.0, 11.0, 10.0, "hidden $h_T$ (32)")
    arrow(ax, 5.0, 8.7,  7.7,  "vector (32)")
    arrow(ax, 5.0, 6.2,  5.2,  "vector (16)")
    arrow(ax, 5.0, 3.8,  2.8,  "scalar prob.")

    # Loss/optim footer (well below blocks)
    ax.text(5.0, 0.4,
            "Loss: weighted binary cross-entropy  ·  "
            "Optim: Adam(lr=$10^{-3}$)  ·  Epochs: 20, batch=128",
            ha="center", va="center", fontsize=10.5, color="#555",
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="#f7f7f7", edgecolor="#cccccc",
                      linewidth=0.6))

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
