"""Ve lai duong cong reward PPO cho dep, tu du lieu huan luyen da luu.

Nguon: thesis-latex/img/exp/ppo_progress.csv
  cum_t : timesteps tich luy CUA MOI moi truong (per-env). Train dung 4 env
          song song nen moi cum_t xuat hien 4 lan. Tong timesteps = cum_t*4.
  r     : tong reward moi episode.   ma : moving average do qua trinh train ghi.

Trinh bay chuan bao cao RL: gop 4 env theo tung moc timesteps -> mean & std;
ve duong mean (dam) + dai +-1 std (mo) thay vi cac gai tung-episode gay
"cut ngan xuong duoi". Truc x = cum_t*4 de khop 400k nhu bao cao.

Output: thesis-latex/img/exp/ppo_reward.png
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "img" / "exp" / "ppo_progress.csv"
OUT = ROOT / "img" / "exp" / "ppo_reward.png"
N_ENVS = 4


def smooth(y, k=5):
    if len(y) < 3:
        return y
    k = min(k, len(y))
    pad = k // 2
    ypad = np.pad(y, (pad, pad), mode="edge")
    return np.convolve(ypad, np.ones(k) / k, mode="same")[pad:pad + len(y)]


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"
    df = pd.read_csv(CSV)
    grp = df.groupby("cum_t")["r"].agg(["mean", "std"]).reset_index()
    grp["std"] = grp["std"].fillna(0.0)
    x = grp["cum_t"].to_numpy() * N_ENVS
    mean = grp["mean"].to_numpy()
    std = grp["std"].to_numpy()
    mean_s = smooth(mean, 5)
    upper = smooth(mean + std, 5)
    lower = smooth(mean - std, 5)
    final = mean_s[-1]

    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.fill_between(x, lower, upper, color="#4a6fa5", alpha=0.18,
                    label="±1 độ lệch chuẩn (4 môi trường)")
    ax.scatter(df["cum_t"].to_numpy() * N_ENVS, df["r"].to_numpy(),
               s=6, color="#9bb0cc", alpha=0.22, linewidths=0,
               label="reward từng episode", zorder=1)
    ax.plot(x, mean_s, color="#1f3a5f", linewidth=2.6,
            label="reward trung bình (đã làm mượt)", zorder=3)

    ax.axhline(final, color="#5ba26c", linestyle="--", linewidth=1.2, alpha=0.9)
    ax.annotate("reward hội tụ ≈ %.0f" % final,
                xy=(x[-1] * 0.95, final), xytext=(x[-1] * 0.50, -4500),
                fontsize=11, color="#2f6b46", weight="bold",
                arrowprops=dict(arrowstyle="->", color="#5ba26c", lw=1.3))
    ax.annotate("pha khám phá ngẫu nhiên\n(để khí vượt ngưỡng liên tục)",
                xy=(x[0], mean[0]), xytext=(x[0] + 55000, mean[0] + 1200),
                fontsize=9.5, color="#8a4a4a", va="center",
                arrowprops=dict(arrowstyle="->", color="#b35b5b", lw=1.1))

    ax.set_title("Đường cong reward huấn luyện PPO trên GasLeakEnv "
                 "(4 môi trường song song)",
                 fontsize=12.5, weight="bold", color="#1f2d3d", pad=10)
    ax.set_xlabel("Tổng số timesteps huấn luyện", fontsize=11.5)
    ax.set_ylabel("Reward mỗi episode", fontsize=11.5)
    ax.grid(True, linestyle=":", alpha=0.45)
    ax.set_xlim(0, x.max() * 1.02)
    ax.legend(loc="lower right", fontsize=9.5, framealpha=0.95)
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: ("%.0fk" % (v / 1000)) if v else "0"))
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print("saved -> %s  (final %.1f, x_max %d)" % (OUT, final, x.max()))


if __name__ == "__main__":
    main()
