# -*- coding: utf-8 -*-
"""Vong lap tuong tac Agent-Environment (RL) -- ban ve lai sach hon.

Sua loi quan trong: cong thuc reward truoc day dung phien ban CU (+10 cho moi
lan giam thieu) khong khop voi reward OUTCOME-BASED (v3) trong code/bao cao.
Phien ban moi the hien dung reward v3.

Output: thesis-latex/img/rl_loop.png
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "rl_loop.png"


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.6)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(6.0, 7.25, "Vòng lặp tương tác Agent–Environment",
            ha="center", va="center", fontsize=15, weight="bold",
            color="#1f2d3d")

    agent_style = dict(boxstyle="round,pad=0.4,rounding_size=0.25",
                       linewidth=2, edgecolor="#1f3a5f", facecolor="#e8eff9")
    env_style = dict(boxstyle="round,pad=0.4,rounding_size=0.25",
                     linewidth=2, edgecolor="#7e3b8e", facecolor="#f0e7f7")
    ax.add_patch(FancyBboxPatch((0.8, 3.6), 3.6, 1.9, **agent_style))
    ax.add_patch(FancyBboxPatch((7.6, 3.6), 3.6, 1.9, **env_style))

    ax.text(2.6, 4.95, "AGENT", ha="center", va="center",
            fontsize=13, weight="bold", color="#1f3a5f")
    ax.text(2.6, 4.30, "PPO policy $\\pi_\\theta$\n(MLP 64–64, actor–critic)",
            ha="center", va="center", fontsize=10.5, color="#33506f")
    ax.text(9.4, 4.95, "ENVIRONMENT", ha="center", va="center",
            fontsize=13, weight="bold", color="#7e3b8e")
    ax.text(9.4, 4.30, "GasLeakEnv\n(máy trạng thái vật lý 4 pha)",
            ha="center", va="center", fontsize=10.5, color="#69477a")

    # Action arrow ABOVE (Agent -> Env)
    ax.add_patch(FancyArrowPatch((4.4, 6.0), (7.6, 6.0),
                 arrowstyle="-|>", mutation_scale=24, linewidth=2.3,
                 color="#c0392b", connectionstyle="arc3,rad=-0.20"))
    ax.text(6.0, 6.72,
            "Hành động $a_t$  (4 rời rạc):\nNO_OP · ALERT · FAN_ON · CLOSE_VALVE",
            ha="center", va="center", fontsize=10.5, color="#c0392b")

    # State+reward arrow BELOW (Env -> Agent)
    ax.add_patch(FancyArrowPatch((7.6, 3.05), (4.4, 3.05),
                 arrowstyle="-|>", mutation_scale=24, linewidth=2.3,
                 color="#1e7f4f", connectionstyle="arc3,rad=-0.20"))
    ax.text(6.0, 2.42,
            "Trạng thái $s_{t+1}$ (8 chiều)  +  Reward $r_{t+1}$",
            ha="center", va="center", fontsize=11, color="#1e7f4f")

    # Decomposition: state vector
    ax.text(6.0, 1.55,
            r"$s_t = (\mathrm{gas},\, T,\, H,\, \mathrm{slope},\, p_{5\min},\,"
            r"\mathrm{fan},\, \mathrm{valve},\, \Delta t_{\mathrm{act}})$",
            ha="center", va="center", fontsize=11)

    # Reward (OUTCOME-BASED v3) -- correct formula
    ax.text(6.0, 0.72,
            r"$r_t = -50\,\mathbb{1}[\mathrm{gas}\!\geq\!1000]"
            r" + 0{,}3\,\mathbb{1}[\mathrm{rò\ rỉ}\ \wedge\ \mathrm{gas}\!<\!1000]"
            r" - \mathrm{chi\ phí}(a_t,s_t) - 0{,}05$",
            ha="center", va="center", fontsize=10.5, color="#444")
    ax.text(6.0, 0.18,
            "(thưởng theo KẾT QUẢ giữ khí dưới ngưỡng; phạt nặng khi vượt ngưỡng "
            "và khi can thiệp sai lúc bình thường)",
            ha="center", va="center", fontsize=8.6, style="italic",
            color="#777")

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
