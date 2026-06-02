"""Generate slide-ready assets for the LSTM forecaster and PPO v3 section.

Run from the project root:

    python slide_model_assets/generate_slide_assets.py

The script reads the current trained-result files under
``thesis-latex/img/exp`` and writes PNGs plus a replacement map into
``slide_model_assets/generated``.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "thesis-latex" / "img" / "exp"
OUT = ROOT / "slide_model_assets" / "generated"

BLUE = "#174f91"
LIGHT_BLUE = "#eaf2fb"
MID_BLUE = "#2e7db8"
TEAL = "#2db8c5"
GREEN = "#4f9954"
RED = "#cf2929"
AMBER = "#efb450"
GRAY = "#989898"
DARK = "#20252b"


def setup_ax(width: float = 16, height: float = 9):
    fig, ax = plt.subplots(figsize=(width, height), dpi=140)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 9)
    ax.axis("off")
    return fig, ax


def box(ax, xy, wh, text, fc="white", ec=DARK, lw=1.4, fontsize=13,
        weight="normal", color=DARK, radius=0.18):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.03,rounding_size={radius}",
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, weight=weight, color=color,
        wrap=True,
    )
    return patch


def arrow(ax, start, end, color=DARK, lw=1.8):
    arr = FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=lw,
        color=color,
        shrinkA=4,
        shrinkB=4,
    )
    ax.add_patch(arr)
    return arr


def title(ax, text, subtitle=None):
    ax.text(8, 8.55, text, ha="center", va="center",
            fontsize=20, weight="bold", color=BLUE)
    if subtitle:
        ax.text(8, 8.15, subtitle, ha="center", va="center",
                fontsize=11.5, color="#59636e")


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def load_json(name):
    return json.loads((EXP / name).read_text(encoding="utf-8"))


def make_lstm_arch():
    fig, ax = setup_ax()
    title(
        ax,
        "LSTM Forecaster",
        "Du bao xac suat gas vuot 1000 ppm trong 5 phut toi",
    )

    box(ax, (0.8, 3.2), (3.5, 2.0),
        "Input window\n60 giay x 3 dac trung\n[gas, temp, humidity]\nnormalized [0,1]",
        fc="#d7eef6", ec=BLUE, fontsize=11.5)
    box(ax, (5.1, 5.9), (2.7, 0.9), "LSTM (32)", fc="#8fd2e6", ec=BLUE,
        fontsize=12.5, weight="bold")
    box(ax, (5.1, 4.6), (2.7, 0.9), "Dropout (0.2)", fc="#f6ed90", ec="#7c7100",
        fontsize=12)
    box(ax, (5.1, 3.3), (2.7, 0.9), "Dense (16, ReLU)", fc="#d8a0d3", ec="#7d3d78",
        fontsize=12)
    box(ax, (5.1, 2.0), (2.7, 0.9), "Dense (1, Sigmoid)", fc="#d8a0d3", ec="#7d3d78",
        fontsize=12)
    box(ax, (9.4, 3.25), (5.2, 2.1),
        "Output\np_critical_5min in [0,1]\nriskLabel: NORMAL / WARNING / ALERT",
        fc="#95ee91", ec=GREEN, fontsize=13, weight="bold")

    arrow(ax, (4.35, 4.2), (5.05, 6.35))
    arrow(ax, (6.45, 5.9), (6.45, 5.5))
    arrow(ax, (6.45, 4.6), (6.45, 4.25))
    arrow(ax, (6.45, 3.3), (6.45, 2.95))
    arrow(ax, (7.85, 2.45), (9.35, 4.25))

    ax.text(1.0, 1.45,
            "Training target: y_t = 1 neu max(gas[t+1:t+300]) > 1000 ppm",
            fontsize=11.5, color="#555")
    ax.text(1.0, 1.05,
            "Khong con bai toan du bao CO 10 buoc; day la forecaster canh bao som 5 phut.",
            fontsize=11.5, color=RED, style="italic")
    save(fig, "01_lstm_forecaster_architecture.png")


def make_ppo_loop():
    fig, ax = setup_ax()
    title(ax, "PPO Control Loop", "Agent dieu khien hanh dong vat ly trong GasLeakEnv")

    box(ax, (1.0, 5.3), (4.3, 1.4),
        "State s_t (8 chieu)\ngas, temp, hum, slope,\np5min, fan, valve, time",
        fc=LIGHT_BLUE, ec=BLUE, fontsize=12)
    box(ax, (6.4, 5.3), (3.0, 1.4), "PPO Agent\nActor-Critic MlpPolicy",
        fc="#fff0cc", ec="#8a6610", fontsize=13, weight="bold")
    box(ax, (10.6, 5.3), (4.2, 1.4),
        "Action a_t\nNO_OP / ALERT_USER\nFAN_ON / CLOSE_VALVE",
        fc="#e9f7e8", ec=GREEN, fontsize=12)
    box(ax, (6.0, 2.0), (4.0, 1.5), "GasLeakEnv\nsimulator 4 pha + vat ly phong",
        fc="#f4f4f4", ec=DARK, fontsize=13, weight="bold")
    box(ax, (1.2, 2.0), (3.9, 1.5),
        "Reward r_t\noutcome-based v3\nbo +10/step reward hacking",
        fc="#fff3f3", ec=RED, fontsize=12)

    arrow(ax, (5.3, 6.0), (6.35, 6.0))
    arrow(ax, (9.45, 6.0), (10.55, 6.0))
    arrow(ax, (12.7, 5.25), (8.3, 3.55))
    arrow(ax, (6.0, 2.75), (5.15, 2.75))
    arrow(ax, (3.2, 3.55), (3.2, 5.25))
    arrow(ax, (8.0, 3.55), (3.6, 5.25))

    ax.text(8.0, 0.95,
            "Muc tieu: giam miss rate va peak gas, khong dieu khien bua khi NORMAL.",
            ha="center", fontsize=12, color="#555")
    save(fig, "02_ppo_control_loop_v3.png")


def draw_table(ax, x, y, col_widths, row_h, headers, rows, title_text=None):
    if title_text:
        ax.text(x + sum(col_widths) / 2, y + row_h * (len(rows) + 1) + 0.35,
                title_text, ha="center", va="bottom", fontsize=15,
                weight="bold", color=BLUE)
    total_w = sum(col_widths)
    n = len(rows) + 1
    for r in range(n):
        yy = y + row_h * (n - 1 - r)
        fc = MID_BLUE if r == 0 else ("#f1f6fb" if r % 2 == 0 else "white")
        ax.add_patch(Rectangle((x, yy), total_w, row_h, facecolor=fc,
                               edgecolor="white", linewidth=1.0))
        xx = x
        vals = headers if r == 0 else rows[r - 1]
        for c, val in enumerate(vals):
            ax.add_line(plt.Line2D([xx, xx], [yy, yy + row_h],
                                   color="white", linewidth=1.0))
            ax.text(xx + 0.12, yy + row_h / 2, val, va="center", ha="left",
                    fontsize=11.5 if r else 12,
                    weight="bold" if r == 0 else "normal",
                    color="white" if r == 0 else DARK)
            xx += col_widths[c]
        ax.add_line(plt.Line2D([x + total_w, x + total_w], [yy, yy + row_h],
                               color="white", linewidth=1.0))
    ax.add_patch(Rectangle((x, y), total_w, row_h * n, fill=False,
                           edgecolor="#d6dce2", linewidth=1.0))


def make_ppo_config():
    fig, ax = setup_ax()
    title(ax, "PPO Training Configuration", "Khac ban cu: 400,000 timesteps + VecNormalize reward")
    rows = [
        ("Algorithm", "PPO"),
        ("Policy", "MlpPolicy"),
        ("Environment", "GasLeakEnv v3"),
        ("Episode length", "1800 s"),
        ("Parallel envs", "4"),
        ("Training steps", "400,000"),
        ("n_steps", "512"),
        ("batch_size", "128"),
        ("gamma", "0.99"),
        ("gae_lambda", "0.95"),
        ("learning_rate", "3e-4"),
        ("ent_coef", "0.01"),
        ("Reward normalization", "VecNormalize(norm_obs=False, norm_reward=True)"),
    ]
    draw_table(ax, 3.2, 0.65, [4.1, 5.5], 0.55, ("Tham so", "Gia tri"), rows)
    save(fig, "03_ppo_training_config.png")


def make_io_table():
    fig, ax = setup_ax()
    title(ax, "PPO Input / Output", "State 8 chieu va 4 hanh dong dieu khien")
    left_rows = [
        ("gas_norm", "Gas hien tai chuan hoa"),
        ("temp_norm", "Nhiet do chuan hoa"),
        ("hum_norm", "Do am chuan hoa"),
        ("slope_norm", "Xu huong tang/giam gas"),
        ("p_critical_5min", "Du doan tu LSTM forecaster"),
        ("fan_on", "Trang thai quat"),
        ("valve_closed", "Trang thai van gas"),
        ("time_since_action", "Thoi gian tu lan dieu khien gan nhat"),
    ]
    right_rows = [
        ("0  NO_OP", "Khong dieu khien"),
        ("1  ALERT_USER", "Canh bao nguoi dung"),
        ("2  FAN_ON", "Bat quat thong gio"),
        ("3  CLOSE_VALVE", "Dong van gas"),
    ]
    draw_table(ax, 0.5, 1.0, [3.2, 4.3], 0.62, ("Bien (8)", "Y nghia"), left_rows,
               "INPUT PPO (8 chieu)")
    draw_table(ax, 8.5, 2.25, [3.2, 4.1], 0.82, ("Action", "Y nghia"), right_rows,
               "OUTPUT PPO (4 hanh dong)")
    save(fig, "04_ppo_input_output_table.png")


def make_reward():
    fig, ax = setup_ax()
    title(ax, "Reward v3 - Outcome Based", "Bo phan thuong +10 moi buoc gay reward hacking")
    formula = (
        r"$R_t=-0.05 - 50\cdot1[gas\geq1000] + 0.3\cdot1[leaking\wedge gas<1000]$"
        "\n"
        r"$-3\cdot1[ALERT,NORMAL] -15\cdot1[FAN,NORMAL] -25\cdot1[VALVE,NORMAL]$"
        "\n"
        r"$-0.5\cdot1[valve\_closed\wedge NORMAL] -0.1\cdot1[fan\_on\wedge NORMAL]$"
    )
    ax.text(8, 7.3, formula, ha="center", va="center", fontsize=14)
    items = [
        (RED, "-50  (gas >= 1000 ppm)", "Phat nang khi de moi truong nguy hiem"),
        (GREEN, "+0.3  (dang ro ri, gas < 1000)", "Thuong theo ket qua kiem soat ro ri"),
        (AMBER, "-3 / -15 / -25 khi NORMAL", "Phat hanh dong sai luc binh thuong"),
        (AMBER, "-0.5 / -0.1 holding cost", "Tranh giu van/quat khong can thiet"),
        (GRAY, "-0.05 moi buoc", "Khuyen khich xu ly dut khoat"),
    ]
    y = 5.4
    for color, score, meaning in items:
        ax.add_patch(Rectangle((1.4, y), 4.2, 0.58, facecolor=color, edgecolor="none"))
        ax.text(3.5, y + 0.29, score, ha="center", va="center",
                fontsize=12, color="white", weight="bold")
        ax.text(6.2, y + 0.29, meaning, ha="left", va="center",
                fontsize=12.5, color=DARK)
        y -= 0.85
    ax.text(8, 0.75,
            "CLOSE_VALVE/FAN_ON khong duoc thuong truc tiep; policy phai lam gas thuc su duoi nguong.",
            ha="center", fontsize=11.5, color="#777", style="italic")
    save(fig, "05_reward_v3_outcome_based.png")


def make_metrics_summary():
    fig, ax = setup_ax()
    title(ax, "Ket Qua Train Moi", "Dung cho slide thay phan CO/UCI cu")
    lstm = load_json("lstm_metrics.json")
    kaggle = load_json("lstm_metrics_kaggle.json")
    latency = load_json("latency_results.json")
    rows = [
        ("LSTM sim accuracy", f"{lstm['accuracy']:.1%}"),
        ("LSTM sim precision", f"{lstm['precision']:.1%}"),
        ("LSTM sim recall", f"{lstm['recall']:.1%}"),
        ("LSTM sim F1", f"{lstm['f1']:.1%}"),
        ("Kaggle validation accuracy", f"{kaggle['accuracy']:.1%}"),
        ("Kaggle validation recall", f"{kaggle['recall']:.1%}"),
        ("Forecaster median latency", f"{latency['forecaster_ms']['median']:.1f} ms"),
        ("PPO median latency", f"{latency['rl_choose_ms']['median']:.2f} ms"),
    ]
    draw_table(ax, 1.2, 2.0, [6.2, 4.0], 0.58, ("Chi so", "Gia tri"), rows)
    ax.text(8, 1.15,
            "LSTM hien du bao p_critical_5min, khong phai hoi quy CO_ppm/R2/MAE nhu slide cu.",
            ha="center", fontsize=12, color=RED)
    save(fig, "06_training_metrics_summary.png")


def make_lstm_training_curve():
    hist = pd.read_csv(EXP / "lstm_history.csv")
    metrics = load_json("lstm_metrics.json")
    epochs = hist["epoch"].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6.2), dpi=150)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "LSTM Forecaster hội tụ ổn định, thiên về ít báo nhầm",
        fontsize=20,
        fontweight="bold",
        color=BLUE,
        y=0.98,
    )
    fig.text(
        0.5,
        0.91,
        "Bài toán: dự báo P(gas vượt 1000 ppm trong 5 phút tới), không phải hồi quy CO ppm",
        ha="center",
        fontsize=11.5,
        color="#5f6975",
    )

    # Panel 1: loss, with raw validation spike kept but visually explained.
    ax = axes[0]
    ax.plot(epochs, hist["loss"], color=BLUE, linewidth=2.4, label="Train loss")
    ax.plot(epochs, hist["val_loss"], color=AMBER, linewidth=2.4, label="Val loss")
    ax.scatter([5], [hist.loc[hist["epoch"] == 5, "val_loss"].iloc[0]],
               s=70, color=RED, zorder=5)
    ax.annotate(
        "temporal spike",
        xy=(5, hist.loc[hist["epoch"] == 5, "val_loss"].iloc[0]),
        xytext=(7.2, 0.58),
        arrowprops=dict(arrowstyle="->", color=RED, lw=1.2),
        fontsize=10,
        color=RED,
    )
    ax.set_title("Loss giảm sau 20 epoch", fontsize=14, fontweight="bold", color=DARK)
    ax.set_xlabel("Epoch", fontsize=10.5, color="#4c5661")
    ax.set_ylabel("Weighted BCE loss", fontsize=10.5, color="#4c5661")
    ax.grid(axis="y", color="#dbe2ea", linewidth=0.9, alpha=0.85)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(labelsize=9.5, colors="#4c5661")
    ax.legend(frameon=False, fontsize=10, loc="upper right")

    # Panel 2: final metrics are more honest than accuracy alone.
    ax = axes[1]
    metric_labels = ["Accuracy", "Precision", "Recall", "F1"]
    metric_vals = [
        metrics["accuracy"],
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
    ]
    metric_colors = [MID_BLUE, GREEN, AMBER, BLUE]
    x = np.arange(len(metric_vals))
    bars = ax.bar(x, np.array(metric_vals) * 100, color=metric_colors, width=0.62)
    ax.set_title("Chất lượng phân loại trên test set", fontsize=14,
                 fontweight="bold", color=DARK)
    ax.set_ylim(0, 110)
    ax.set_ylabel("%", fontsize=10.5, color="#4c5661")
    ax.set_xticks(x, metric_labels, fontsize=10.5)
    ax.grid(axis="y", color="#dbe2ea", linewidth=0.9, alpha=0.85)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(axis="y", labelsize=9.5, colors="#4c5661")
    for bar, val in zip(bars, metric_vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val * 100 + 3,
            f"{val:.1%}",
            ha="center",
            fontsize=11,
            fontweight="bold",
            color=DARK,
        )

    info = (
        f"Test samples: {metrics['samples_test']:,}   "
        f"Positive rate: {metrics['positive_rate']:.1%}   "
        f"TP/FP/TN/FN: {metrics['tp']}/{metrics['fp']}/{metrics['tn']}/{metrics['fn']}"
    )
    fig.text(0.5, 0.07, info, ha="center", fontsize=11, color="#5f6975")
    fig.text(
        0.5,
        0.035,
        "Diễn giải: Precision cao -> ít cảnh báo nhầm; Recall trung bình -> model bảo thủ, nên PPO vẫn dùng thêm gas/slope/state để quyết định.",
        ha="center",
        fontsize=11.2,
        color=BLUE,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0.03, 0.11, 0.98, 0.86], w_pad=3.0)
    save(fig, "07_lstm_training_curve.png")


def make_controller_benchmark():
    data = load_json("benchmark_results.json")
    controllers = ["threshold", "forecaster", "rule", "rl"]
    labels = ["Threshold", "LSTM\nalert", "Rule\ncontrol", "PPO RL"]
    colors = ["#b8bec6", "#66a6d9", "#efb450", "#d62728"]

    panels = [
        ("miss_rate", "Tỷ lệ bỏ sót", "% lượt rò rỉ chạm 1000 ppm", 100.0, "lower"),
        ("alarms_per_hour", "Cảnh báo sai", "cảnh báo / giờ", 1.0, "lower"),
        ("mean_peak_gas", "Đỉnh nồng độ gas", "ppm trung bình", 1.0, "lower"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(16, 6.2), dpi=150)
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "PPO v3 giảm rò rỉ nguy hiểm và đỉnh gas tốt nhất",
        fontsize=20,
        fontweight="bold",
        color=BLUE,
        y=0.98,
    )
    fig.text(
        0.5,
        0.91,
        "Benchmark 3 seeds x 4h - giá trị càng thấp càng tốt",
        ha="center",
        fontsize=11.5,
        color="#5f6975",
    )

    for ax, (metric, heading, ylabel, scale, _direction) in zip(axes, panels):
        vals = np.array([data[c][metric][0] * scale for c in controllers], dtype=float)
        errs = np.array([data[c][metric][1] * scale for c in controllers], dtype=float)
        x = np.arange(len(vals))
        bars = ax.bar(
            x,
            vals,
            yerr=errs,
            capsize=4,
            color=colors,
            edgecolor="none",
            width=0.64,
            zorder=3,
        )
        ax.set_title(heading, fontsize=14, fontweight="bold", color=DARK, pad=12)
        ax.set_ylabel(ylabel, fontsize=10.5, color="#4c5661")
        ax.set_xticks(x, labels, fontsize=10)
        ax.tick_params(axis="y", labelsize=9.5, colors="#4c5661")
        ax.grid(axis="y", color="#dbe2ea", linewidth=0.9, alpha=0.85, zorder=0)
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.set_axisbelow(True)

        top = max(vals + errs)
        ax.set_ylim(0, top * 1.28 if top else 1)

        for i, (bar, val) in enumerate(zip(bars, vals)):
            if metric == "miss_rate":
                label = f"{val:.0f}%"
            elif metric == "alarms_per_hour":
                label = f"{val:.1f}/h"
            else:
                label = f"{val:.0f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + top * 0.045,
                label,
                ha="center",
                va="bottom",
                fontsize=10.5,
                fontweight="bold" if i == 3 else "normal",
                color=DARK,
            )

        # Highlight PPO as the result worth remembering at thumbnail size.
        bars[-1].set_edgecolor("#8b0000")
        bars[-1].set_linewidth(1.4)

    fig.text(
        0.5,
        0.04,
        "Kết luận: PPO RL can thiệp vật lý đúng lúc nên miss rate còn 5%, cảnh báo ít nhất và peak gas chỉ ~222 ppm.",
        ha="center",
        fontsize=12.5,
        color=BLUE,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0.03, 0.1, 0.98, 0.86], w_pad=2.2)
    save(fig, "11_controller_benchmark_chart.png")


def copy_existing_result_images():
    mapping = {
        "lstm_confusion_matrix.png": "08_lstm_confusion_matrix_sim.png",
        "lstm_confusion_matrix_kaggle.png": "09_lstm_confusion_matrix_kaggle.png",
        "ppo_reward.png": "10_ppo_reward_curve.png",
        "scenarios_chart.png": "12_scenario_benchmark_chart.png",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for src, dst in mapping.items():
        src_path = EXP / src
        if src_path.exists():
            shutil.copy2(src_path, OUT / dst)


def write_replacement_map():
    text = """# Slide Replacement Map

Use these generated PNGs to replace the old model/result figures in
`BasoCaoKLTN2_6_2026 (1).pptx`.

| Old slide | Problem in old slide | Replacement asset |
|---|---|---|
| 6 | LSTM architecture has 64+32 LSTM, BatchNorm, and CO-style target | `01_lstm_forecaster_architecture.png` |
| 7 | Generic RL loop, not specific to GasLeakEnv/PPO | `02_ppo_control_loop_v3.png` |
| 8 | PPO config should stay v3/400k/VecNormalize | `03_ppo_training_config.png` |
| 9 | Input/output table should use 8-state gas controller and 4 actions | `04_ppo_input_output_table.png` |
| 10 | Reward slide should emphasize outcome-based v3 and removed +10 farming | `05_reward_v3_outcome_based.png` |
| 11-15 | Old CO/UCI regression progress and 200k PPO figures are obsolete | `06_training_metrics_summary.png`, `07_lstm_training_curve.png`, `10_ppo_reward_curve.png`, `11_controller_benchmark_chart.png` |
| Results/benchmark slides | Need final controller evidence | `11_controller_benchmark_chart.png`, `12_scenario_benchmark_chart.png` |

Key facts for narration:

- LSTM task: predict `p_critical_5min = P(max gas[t+1:t+300] > 1000 ppm)`.
- LSTM input: 60 seconds x 3 features (`gas_ppm`, `temperature_c`, `humidity_percent`).
- PPO input: 8-dimensional state including LSTM `p_critical_5min`.
- PPO output: `NO_OP`, `ALERT_USER`, `FAN_ON`, `CLOSE_VALVE`.
- PPO training: 400,000 timesteps, 4 parallel envs, `VecNormalize(norm_obs=False, norm_reward=True)`.
- Reward v3 removes the old direct `+10/action-step` incentive and rewards actual containment.
"""
    (OUT / "replacement_map.md").write_text(text, encoding="utf-8")


def main():
    make_lstm_arch()
    make_ppo_loop()
    make_ppo_config()
    make_io_table()
    make_reward()
    make_metrics_summary()
    make_lstm_training_curve()
    make_controller_benchmark()
    copy_existing_result_images()
    write_replacement_map()
    print(f"Generated slide assets in: {OUT}")


if __name__ == "__main__":
    main()
