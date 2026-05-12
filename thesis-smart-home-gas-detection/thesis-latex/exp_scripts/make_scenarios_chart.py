"""Bar chart per scenario × controller × metric.

Reads thesis-latex/img/exp/scenarios_results.json.
Outputs thesis-latex/img/exp/scenarios_chart.png
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "img" / "exp" / "scenarios_results.json"
OUT = ROOT / "img" / "exp" / "scenarios_chart.png"

CONTROLLERS = ["threshold", "forecaster", "rl"]
COLORS = ["#9aa6b2", "#4a86b8", "#3d8a5e"]
EDGE = "#2c3e50"
SCEN_LABEL = {"idle": "TC-Idle", "slow": "TC-Slow", "fast": "TC-Fast"}


def main() -> None:
    data = json.loads(DATA.read_text())
    agg = data["aggregated"]

    def get(scenario, ctrl, key):
        for r in agg:
            if r["scenario"] == scenario and r["controller"] == ctrl:
                return r[f"{key}_mean"], r[f"{key}_std"]
        return 0.0, 0.0

    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 9))

    metric_specs = [
        ("lead_time_s",    "Lead time (giây)",     False, axes[0, 0]),
        ("miss_rate",      "Miss rate (%)",        True,  axes[0, 1]),
        ("alarms_per_hour", "False alarm / giờ",   True,  axes[1, 0]),
        ("mean_peak_gas",  "Peak gas (ppm)",       True,  axes[1, 1]),
    ]

    scenarios = ["idle", "slow", "fast"]
    x = np.arange(len(scenarios))
    width = 0.27

    for key, title, lower_better, ax in metric_specs:
        # First, gather all data so we know the max for ylim sizing.
        per_ctrl_means: list[list[float]] = []
        per_ctrl_stds: list[list[float]] = []
        for ctrl in CONTROLLERS:
            means, stds = [], []
            for sc in scenarios:
                m, s = get(sc, ctrl, key)
                if key == "miss_rate":
                    m *= 100.0
                    s *= 100.0
                means.append(m)
                stds.append(s)
            per_ctrl_means.append(means)
            per_ctrl_stds.append(stds)

        max_top = max(
            (m + s) for ms, ss in zip(per_ctrl_means, per_ctrl_stds)
            for m, s in zip(ms, ss)
        )
        # Add 18% headroom for value labels so they never collide with error caps.
        ax.set_ylim(0, max(max_top * 1.18, 1.0))
        label_offset = max(max_top * 0.04, 0.05)

        for i, ctrl in enumerate(CONTROLLERS):
            means = per_ctrl_means[i]
            stds = per_ctrl_stds[i]
            bars = ax.bar(x + (i - 1) * width, means, width,
                          yerr=stds, capsize=4,
                          color=COLORS[i], edgecolor=EDGE,
                          linewidth=0.8,
                          label=ctrl.upper(),
                          error_kw=dict(lw=1.0))
            for b, m, s in zip(bars, means, stds):
                if m > 1e-3:
                    if key in ("mean_peak_gas", "lead_time_s"):
                        label = f"{m:.0f}"
                    else:
                        label = f"{m:.1f}"
                    ax.text(b.get_x() + b.get_width() / 2,
                            b.get_height() + s + label_offset,
                            label,
                            ha="center", va="bottom",
                            fontsize=9, color="#222", weight="bold")

        ax.set_xticks(x)
        ax.set_xticklabels([SCEN_LABEL[s] for s in scenarios], fontsize=10.5)
        ax.set_title(title, fontsize=12.5, weight="bold", pad=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, axis="y", alpha=0.25, linestyle="--", zorder=0)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", labelsize=9)

        badge = "↑ cao = tốt hơn" if not lower_better else "↓ thấp = tốt hơn"
        ax.text(0.99, 0.97, badge, transform=ax.transAxes,
                ha="right", va="top", fontsize=9, color="#555",
                bbox=dict(boxstyle="round,pad=0.25",
                          facecolor="#f3f4f6",
                          edgecolor="#cccccc", linewidth=0.6))

    # Single legend at top
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, ec=EDGE)
               for c in COLORS]
    fig.legend(handles, [c.upper() for c in CONTROLLERS],
               loc="upper center", ncol=3,
               bbox_to_anchor=(0.5, 0.99), frameon=False, fontsize=11)

    fig.suptitle(
        "Kết quả 3 kịch bản thực nghiệm × 3 bộ điều khiển × 3 seed",
        fontsize=13.5, weight="bold", y=0.945,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(OUT, dpi=150, facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
