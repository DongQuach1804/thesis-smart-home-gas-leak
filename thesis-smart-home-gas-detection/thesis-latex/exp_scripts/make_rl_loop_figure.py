"""Generate the canonical Agent-Environment interaction loop diagram for RL.

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


def main() -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # Title at top
    ax.text(6.0, 6.9,
            "Vòng lặp tương tác Agent–Environment",
            ha="center", va="center", fontsize=14, weight="bold")

    box_style = dict(
        boxstyle="round,pad=0.4",
        linewidth=2,
        edgecolor="#1f3a5f",
        facecolor="#e8eff9",
    )
    # Boxes
    agent_box = FancyBboxPatch((0.8, 3.2), 3.4, 1.8, **box_style)
    env_box = FancyBboxPatch((7.8, 3.2), 3.4, 1.8, **box_style)
    ax.add_patch(agent_box)
    ax.add_patch(env_box)

    ax.text(2.5, 4.1, "Agent\n(PPO policy $\\pi_\\theta$)",
            ha="center", va="center", fontsize=13, weight="bold", color="#1f3a5f")
    ax.text(9.5, 4.1, "Environment\n(GasLeakEnv)",
            ha="center", va="center", fontsize=13, weight="bold", color="#1f3a5f")

    # Action arrow ABOVE boxes (Agent -> Env)
    action_arrow = FancyArrowPatch(
        (3.5, 5.6), (8.5, 5.6),
        arrowstyle="-|>", mutation_scale=24,
        linewidth=2.2, color="#c0392b",
        connectionstyle="arc3,rad=-0.18",
    )
    ax.add_patch(action_arrow)
    ax.text(6.0, 6.25,
            r"Action $a_t \in$ {NO_OP, ALERT, FAN, VALVE}",
            ha="center", va="center", fontsize=12, color="#c0392b")

    # State arrow BELOW boxes (Env -> Agent)
    state_arrow = FancyArrowPatch(
        (8.5, 2.6), (3.5, 2.6),
        arrowstyle="-|>", mutation_scale=24,
        linewidth=2.2, color="#1e7f4f",
        connectionstyle="arc3,rad=-0.18",
    )
    ax.add_patch(state_arrow)
    ax.text(6.0, 1.95,
            r"State $s_{t+1}$ (8-dim), Reward $r_{t+1}$",
            ha="center", va="center", fontsize=12, color="#1e7f4f")

    # Decomposition lines at bottom
    ax.text(6.0, 1.05,
            r"$s_t = (\mathrm{gas},\; T,\; H,\; \mathrm{slope},\; p_{5\min},\;"
            r"\mathrm{fan},\; \mathrm{valve},\; \Delta t_{\mathrm{act}})$",
            ha="center", va="center", fontsize=11)
    ax.text(6.0, 0.45,
            r"$r_t = -50\,\mathbb{1}[\mathrm{gas}\!\geq\!1000]"
            r"+ 10\,\mathbb{1}[\mathrm{mitigation\;in\;leak}]"
            r"+ \mathrm{cost}(a_t, s_t) - 0{,}05$",
            ha="center", va="center", fontsize=10.5, color="#444")

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
