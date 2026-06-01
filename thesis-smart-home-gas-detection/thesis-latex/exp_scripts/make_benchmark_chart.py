"""Bar chart visualising benchmark results (3 controllers x 4 metrics).

Output: thesis-latex/img/exp/benchmark_chart.png
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "exp" / "benchmark_chart.png"

CONTROLLERS = ["THRESHOLD", "FORECASTER", "RL"]
# Softer, thesis-friendly palette
COLORS = ["#9aa6b2", "#4a86b8", "#3d8a5e"]
EDGE = "#2c3e50"

LEAD_MEAN = [35.0, 138.0, 1803.0]
LEAD_STD  = [5.0,  26.0,  755.0]

MISS_MEAN = [0.0, 4.2, 15.0]
MISS_STD  = [0.0, 5.9, 10.8]

ALARM_MEAN = [2.8, 5.6, 0.2]
ALARM_STD  = [1.0, 1.1, 0.0]

PEAK_MEAN = [1508.0, 1508.0, 63.0]
PEAK_STD  = [88.0,   88.0,   0.0]


def panel(ax, values, errors, title, ylabel, lower_better=True,
          log=False, ymax=None, ymin=0, value_fmt="{:.1f}"):
    x = np.arange(len(CONTROLLERS))
    width = 0.55
    bars = ax.bar(x, values, width=width,
                  yerr=errors, capsize=5,
                  color=COLORS, edgecolor=EDGE, linewidth=1.0,
                  error_kw=dict(ecolor="#2c3e50", lw=1.2))

    ax.set_xticks(x)
    ax.set_xticklabels(CONTROLLERS, fontsize=10.5)
    ax.set_ylabel(ylabel, fontsize=10.5)
    ax.set_title(title, fontsize=12.5, weight="bold", pad=10)
    if log:
        ax.set_yscale("log")
        ax.set_ylim(bottom=max(ymin, 1))
    else:
        if ymax is None:
            ymax = max(v + e for v, e in zip(values, errors)) * 1.20
        ax.set_ylim(ymin, ymax)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=9.5)
    ax.grid(True, axis="y", alpha=0.25, linestyle="--", zorder=0)
    ax.set_axisbelow(True)

    # Annotate values above error bars
    for b, v, e in zip(bars, values, errors):
        cap_top = v + e
        label = value_fmt.format(v)
        if log:
            y_offset = cap_top * 1.10
        else:
            y_offset = cap_top + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.03
        ax.text(b.get_x() + b.get_width() / 2, y_offset, label,
                ha="center", va="bottom", fontsize=10.5, weight="bold",
                color="#1f2d3d")

    direction = "↑ cao hơn = tốt hơn" if not lower_better else "↓ thấp hơn = tốt hơn"
    ax.text(0.99, 0.97, direction, transform=ax.transAxes,
            ha="right", va="top", fontsize=9, color="#555",
            bbox=dict(boxstyle="round,pad=0.25",
                      facecolor="#f3f4f6", edgecolor="#cccccc", linewidth=0.6))


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))

    panel(axes[0, 0], LEAD_MEAN, LEAD_STD,
          "Lead time (giây)", "$lead\\_time_s$",
          lower_better=False, log=True, ymin=10, value_fmt="{:.0f}")
    panel(axes[0, 1], MISS_MEAN, MISS_STD,
          "Miss rate (%)", "$miss\\_rate$ (%)",
          ymax=32, value_fmt="{:.1f}")
    panel(axes[1, 0], ALARM_MEAN, ALARM_STD,
          "False alarm rate (alarms/giờ)", "$alarms\\_per\\_hour$",
          ymax=8, value_fmt="{:.1f}")
    panel(axes[1, 1], PEAK_MEAN, PEAK_STD,
          "Mean peak gas (ppm)", "$mean\\_peak\\_gas$ (ppm)",
          ymax=1800, value_fmt="{:.0f}")

    fig.suptitle(
        "So sánh ba bộ điều khiển trên 4 chỉ số đánh giá\n"
        "(3 seeds × 4 giờ mô phỏng, error bar = độ lệch chuẩn)",
        fontsize=13.5, weight="bold", y=0.99,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
