"""Block diagram of the PPO MLP policy/value network for GasLeakEnv.

Stable-Baselines3 MlpPolicy (default): two hidden layers of 64 units,
tanh activations, shared trunk, separate policy head (4 logits) and
value head (scalar).

Output: thesis-latex/img/ppo_arch.png
Run:    python thesis-latex/exp_scripts/make_ppo_arch_figure.py
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "ppo_arch.png"


def block(ax, x, y, w, h, title, sub, fill, border, fs=12):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.18,rounding_size=0.18",
        linewidth=1.7, edgecolor=border, facecolor=fill,
    )
    ax.add_patch(box)
    if sub:
        ax.text(x + w / 2, y + h * 0.66, title,
                ha="center", va="center", fontsize=fs, weight="bold",
                color="#1f2d3d")
        ax.text(x + w / 2, y + h * 0.28, sub,
                ha="center", va="center", fontsize=fs - 2.5,
                color="#445063")
    else:
        ax.text(x + w / 2, y + h / 2, title,
                ha="center", va="center", fontsize=fs, weight="bold",
                color="#1f2d3d")


def arrow(ax, x1, y1, x2, y2, color="#34495e", label=None, label_xy=None,
          lw=1.7):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=17, linewidth=lw, color=color,
    )
    ax.add_patch(a)
    if label and label_xy:
        ax.text(label_xy[0], label_xy[1], label,
                ha="center", va="center", fontsize=10, color=color,
                bbox=dict(boxstyle="round,pad=0.22",
                          facecolor="white", edgecolor="#d0d0d0",
                          linewidth=0.6))


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(17, 11))
    ax.set_xlim(0, 26)
    ax.set_ylim(0, 14)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(13.0, 13.3,
            "Kiến trúc PPO (Actor--Critic) cho GasLeakEnv",
            ha="center", va="center", fontsize=17, weight="bold",
            color="#1f2d3d")

    obs_fill, obs_b = "#fef3e6", "#e8a25b"
    mlp_fill, mlp_b = "#e7eef8", "#4a6fa5"
    pol_fill, pol_b = "#fae7e7", "#b35b5b"
    val_fill, val_b = "#e6f4ea", "#5ba26c"
    env_fill, env_b = "#f0e7f7", "#7e3b8e"

    # -------- TOP ROW: feed-forward pipeline --------
    y_row = 8.0
    h_row = 2.6

    block(ax, 0.5, y_row, 4.5, h_row,
          "State $s_t$ (8 chiều)",
          "gas, T, H, slope, $p_{5\\min}$,\n"
          "fan, valve, $\\Delta t_{\\mathrm{act}}$\n"
          "chuẩn hoá $[0,1]$",
          obs_fill, obs_b)

    block(ax, 6.2, y_row, 3.6, h_row,
          "Dense 64",
          "tanh\n$8 \\to 64$\n576 tham số",
          mlp_fill, mlp_b)

    block(ax, 10.8, y_row, 3.6, h_row,
          "Dense 64",
          "tanh\n$64 \\to 64$\n$4{,}160$ tham số",
          mlp_fill, mlp_b)

    # Heads vertical split
    block(ax, 15.7, y_row + 1.50, 3.8, 1.55,
          "Policy head",
          "Dense $64 \\to 4$  ·  logits",
          pol_fill, pol_b, fs=11.5)
    block(ax, 20.3, y_row + 1.50, 5.2, 1.55,
          "Softmax $\\pi_\\theta(a|s)$",
          "NO_OP / ALERT / FAN / VALVE",
          pol_fill, pol_b, fs=11.5)

    block(ax, 15.7, y_row - 0.05, 3.8, 1.55,
          "Value head",
          "Dense $64 \\to 1$",
          val_fill, val_b, fs=11.5)
    block(ax, 20.3, y_row - 0.05, 5.2, 1.55,
          "$V_\\phi(s)$ — scalar",
          "ước lượng giá trị trạng thái",
          val_fill, val_b, fs=11.5)

    # Horizontal pipeline arrows
    y_mid = y_row + h_row / 2
    arrow(ax, 5.0, y_mid, 6.2, y_mid, label="(8)",
          label_xy=(5.6, y_mid + 0.5))
    arrow(ax, 9.8, y_mid, 10.8, y_mid, label="(64)",
          label_xy=(10.3, y_mid + 0.5))

    # Split arrows from trunk to heads
    arrow(ax, 14.4, y_mid, 15.7, y_row + 2.27, label="(64)",
          label_xy=(14.95, y_mid + 0.85))
    arrow(ax, 14.4, y_mid, 15.7, y_row + 0.72, label="(64)",
          label_xy=(14.95, y_mid - 0.85))

    # Heads -> outputs
    arrow(ax, 19.5, y_row + 2.27, 20.3, y_row + 2.27, color="#b35b5b")
    arrow(ax, 19.5, y_row + 0.72, 20.3, y_row + 0.72, color="#5ba26c")

    # -------- BOTTOM ROW: agent-env loop --------
    block(ax, 17.5, 3.4, 8.0, 2.0,
          "Action sampler",
          "$a_t \\sim \\pi_\\theta(\\cdot | s_t)$  ·  4 hành động rời rạc",
          pol_fill, pol_b, fs=12)

    block(ax, 4.5, 3.4, 9.5, 2.0,
          "GasLeakEnv (gymnasium)",
          "physical state machine  ·  trả về $s_{t+1}, r_{t+1}$",
          env_fill, env_b, fs=12)

    # Loop arrows
    arrow(ax, 22.9, y_row + 1.5, 22.9, 5.4, color="#b35b5b",
          label="$\\pi_\\theta$", label_xy=(23.5, 6.7))
    arrow(ax, 17.5, 4.4, 14.0, 4.4, color="#b35b5b",
          label="$a_t$", label_xy=(15.75, 4.85))
    arrow(ax, 4.5, 4.4, 2.5, 4.4, color="#7e3b8e")
    arrow(ax, 2.5, 4.4, 2.5, 8.0, color="#7e3b8e",
          label="$s_{t+1}, r_{t+1}$", label_xy=(1.3, 6.2))

    # Subtle separator
    ax.plot([0.5, 25.5], [6.9, 6.9], color="#cccccc",
            linewidth=0.8, linestyle="--")
    ax.text(0.5, 7.20,
            "Neural network (forward pass)",
            ha="left", va="center", fontsize=10.5, style="italic",
            color="#777")
    ax.text(0.5, 6.60,
            "Vòng tương tác Agent--Environment",
            ha="left", va="center", fontsize=10.5, style="italic",
            color="#777")

    # Hyperparameters footer
    ax.text(13.0, 1.3,
            "PPO: clip $\\epsilon = 0{,}2$  ·  $\\gamma=0{,}99$  ·  "
            "$\\lambda_{\\mathrm{GAE}}=0{,}95$  ·  "
            "lr $= 3 \\times 10^{-4}$  ·  ent_coef $= 0{,}01$  ·  "
            "n_envs=4, n_steps=512, batch=128",
            ha="center", va="center", fontsize=11, color="#555",
            bbox=dict(boxstyle="round,pad=0.4",
                      facecolor="#f7f7f7", edgecolor="#cccccc",
                      linewidth=0.6))

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
