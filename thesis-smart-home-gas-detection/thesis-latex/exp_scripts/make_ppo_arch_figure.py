# -*- coding: utf-8 -*-
"""So do khoi kien truc PPO actor-critic cho GasLeakEnv -- ban ve lai sach hon.

SB3 MlpPolicy (mac dinh): trunk dung chung 2 lop Dense 64 (tanh), tach policy
head (4 logits -> softmax) va value head (scalar). Phien ban nay bo cuc gon,
khong con doan "cut" o phia duoi, vong lap agent-env duoc noi lien mach.

Output: thesis-latex/img/ppo_arch.png
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
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.16,rounding_size=0.16",
        linewidth=1.8, edgecolor=border, facecolor=fill))
    if sub:
        ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center",
                fontsize=fs, weight="bold", color="#1f2d3d")
        ax.text(x + w / 2, y + h * 0.27, sub, ha="center", va="center",
                fontsize=fs - 2.5, color="#445063")
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                fontsize=fs, weight="bold", color="#1f2d3d")


def arrow(ax, x1, y1, x2, y2, color="#34495e", label=None, lxy=None, lw=1.8,
          rad=0.0):
    cs = ("arc3,rad=%s" % rad) if rad else None
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=18, linewidth=lw, color=color,
                 connectionstyle=cs))
    if label and lxy:
        ax.text(lxy[0], lxy[1], label, ha="center", va="center",
                fontsize=10, color=color,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor="#d0d0d0", linewidth=0.6))


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(15, 8.2))
    ax.set_xlim(0, 26)
    ax.set_ylim(0, 14)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(13.0, 13.4, "Kiến trúc PPO (Actor–Critic) cho GasLeakEnv",
            ha="center", va="center", fontsize=16.5, weight="bold",
            color="#1f2d3d")

    obs_f, obs_b = "#fef3e6", "#e8a25b"
    mlp_f, mlp_b = "#e7eef8", "#4a6fa5"
    pol_f, pol_b = "#fae7e7", "#b35b5b"
    val_f, val_b = "#e6f4ea", "#5ba26c"
    env_f, env_b = "#f0e7f7", "#7e3b8e"

    yr, hr = 8.4, 2.6
    block(ax, 0.5, yr, 4.6, hr, "Trạng thái $s_t$ (8 chiều)",
          "gas, T, H, slope, $p_{5\\min}$,\nfan, valve, $\\Delta t_{\\mathrm{act}}$ — chuẩn hoá [0,1]",
          obs_f, obs_b)
    block(ax, 6.4, yr, 3.5, hr, "Dense 64", "tanh · $8\\to64$\n576 tham số", mlp_f, mlp_b)
    block(ax, 10.9, yr, 3.5, hr, "Dense 64", "tanh · $64\\to64$\n4.160 tham số", mlp_f, mlp_b)

    # Heads
    block(ax, 15.7, yr + 1.45, 3.7, 1.5, "Policy head", "Dense $64\\to4$ · logits", pol_f, pol_b, fs=11)
    block(ax, 20.2, yr + 1.45, 5.3, 1.5, "Softmax $\\pi_\\theta(a|s)$", "NO_OP/ALERT/FAN/VALVE", pol_f, pol_b, fs=11)
    block(ax, 15.7, yr - 0.05, 3.7, 1.5, "Value head", "Dense $64\\to1$", val_f, val_b, fs=11)
    block(ax, 20.2, yr - 0.05, 5.3, 1.5, "$V_\\phi(s)$ — scalar", "ước lượng giá trị", val_f, val_b, fs=11)

    ym = yr + hr / 2
    arrow(ax, 5.1, ym, 6.4, ym, label="(8)", lxy=(5.75, ym + 0.55))
    arrow(ax, 9.9, ym, 10.9, ym, label="(64)", lxy=(10.4, ym + 0.55))
    arrow(ax, 14.4, ym, 15.7, yr + 2.2, label="(64)", lxy=(15.0, ym + 0.9))
    arrow(ax, 14.4, ym, 15.7, yr + 0.7, label="(64)", lxy=(15.0, ym - 0.9))
    arrow(ax, 19.4, yr + 2.2, 20.2, yr + 2.2, color="#b35b5b")
    arrow(ax, 19.4, yr + 0.7, 20.2, yr + 0.7, color="#5ba26c")

    # ----- Agent-Environment loop (noi lien mach, khong cut) -----
    block(ax, 16.0, 3.3, 9.5, 2.0, "Action sampler",
          "$a_t \\sim \\pi_\\theta(\\cdot|s_t)$ · 4 hành động rời rạc", pol_f, pol_b, fs=12)
    block(ax, 3.5, 3.3, 9.5, 2.0, "GasLeakEnv (gymnasium)",
          "máy trạng thái vật lý · trả về $s_{t+1}, r_{t+1}$", env_f, env_b, fs=12)

    # softmax -> action sampler (di xuong)
    arrow(ax, 22.85, yr + 1.45, 22.85, 5.3, color="#b35b5b",
          label="$\\pi_\\theta(a|s)$", lxy=(24.0, 6.9), rad=0.0)
    # action sampler -> env
    arrow(ax, 16.0, 4.3, 13.0, 4.3, color="#b35b5b", label="$a_t$", lxy=(14.5, 4.75))
    # env -> state (di len, khep vong)
    arrow(ax, 3.5, 4.3, 2.4, 4.3, color="#7e3b8e")
    arrow(ax, 2.4, 4.3, 2.4, 8.4, color="#7e3b8e",
          label="$s_{t+1}, r_{t+1}$", lxy=(1.25, 6.4))

    ax.text(0.6, 7.55, "Mạng nơ-ron (lượt truyền xuôi)", ha="left",
            va="center", fontsize=10, style="italic", color="#888")
    ax.text(0.6, 5.75, "Vòng tương tác Agent–Environment", ha="left",
            va="center", fontsize=10, style="italic", color="#888")
    ax.plot([0.5, 25.5], [6.75, 6.75], color="#cccccc", lw=0.9, ls="--")

    ax.text(13.0, 1.55,
            "PPO: clip $\\epsilon=0{,}2$ · $\\gamma=0{,}99$ · "
            "$\\lambda_{\\mathrm{GAE}}=0{,}95$ · lr $=3\\times10^{-4}$ · "
            "ent_coef $=0{,}01$ · n_envs=4 · n_steps=512 · batch=128 · "
            "VecNormalize · tổng ~5.060 tham số",
            ha="center", va="center", fontsize=10.5, color="#555",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f7f7f7",
                      edgecolor="#cccccc", linewidth=0.6))

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
