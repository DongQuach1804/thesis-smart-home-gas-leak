# -*- coding: utf-8 -*-
"""So do kien truc he thong 4 tang (system implementation) -- ban ve lai sach.

Cai tien so voi ban truoc: bo cuc luong ngang ro rang trong tang Xu ly, dinh
tuyen cac mui ten cheo (alert events / write) gon hon, nhan khong de len nhau.

Output: thesis-latex/img/architecture.png
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "img" / "architecture.png"

LAYER = {
    "device": ("#fef3e6", "#e8a25b"),
    "comm":   ("#e6f4ea", "#5ba26c"),
    "proc":   ("#e7eef8", "#4a6fa5"),
    "app":    ("#fae7e7", "#b35b5b"),
}
DARK = "#1f2d3d"


def box(ax, x, y, w, h, text, key, fs=11, sub=None):
    fill, border = LAYER[key]
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0.16,rounding_size=0.16",
                 linewidth=1.7, edgecolor=border, facecolor=fill))
    if sub:
        ax.text(x + w / 2, y + h * 0.64, text, ha="center", va="center",
                fontsize=fs, weight="bold", color=DARK)
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center",
                fontsize=fs - 2, color="#4a5566")
    else:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, weight="bold", color=DARK)


def band(ax, y, h, label, sub, key, xl=2.6, xr=23.4):
    fill, border = LAYER[key]
    ax.add_patch(plt.Rectangle((xl, y), xr - xl, h, facecolor=fill,
                 alpha=0.26, edgecolor=border, linewidth=1.0))
    ax.text(0.5, y + h * 0.62, label, ha="left", va="center", fontsize=13,
            weight="bold", color=border)
    ax.text(0.5, y + h * 0.27, sub, ha="left", va="center", fontsize=9,
            style="italic", color="#666")


def arrow(ax, x1, y1, x2, y2, label=None, lxy=None, color="#34495e", lw=1.5,
          rad=0.0):
    cs = ("arc3,rad=%s" % rad) if rad else None
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=13, linewidth=lw, color=color,
                 connectionstyle=cs))
    if label and lxy:
        ax.text(lxy[0], lxy[1], label, ha="center", va="center", fontsize=9,
                color=color, bbox=dict(boxstyle="round,pad=0.2",
                facecolor="white", edgecolor="#d0d0d0", linewidth=0.6,
                alpha=0.97))


def main():
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 23.6)
    ax.set_ylim(0, 13.6)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(12.0, 13.1, "Kiến trúc hệ thống 4 tầng", ha="center",
            va="center", fontsize=17, weight="bold", color=DARK)

    band(ax, 10.5, 2.1, "Ứng dụng", "Frontend, API, cảnh báo", "app")
    band(ax, 6.4, 3.4, "Xử lý", "Streaming + suy luận ML", "proc")
    band(ax, 4.0, 1.8, "Truyền thông", "MQTT / Kafka", "comm")
    band(ax, 1.4, 2.0, "Thiết bị", "Cảm biến + bộ mô phỏng", "device")

    # ---- Device ----
    box(ax, 4.6, 1.7, 4.4, 1.4, "ESP32 + MQ-2/DHT22", "device",
        sub="C++/Arduino · 1 Hz")
    box(ax, 9.8, 1.7, 4.4, 1.4, "Sensor Simulator", "device",
        sub="Python · máy trạng thái")
    box(ax, 15.2, 1.7, 4.6, 1.4, "MQTT publish", "device",
        sub="topic: sensors/gas")

    # ---- Comm ----
    box(ax, 6.0, 4.3, 5.2, 1.2, "Mosquitto Broker", "comm",
        sub="port 1883 · persistence")
    box(ax, 13.5, 4.3, 5.6, 1.2, "mqtt_kafka_bridge", "comm",
        sub="MQTT → Kafka")

    # ---- Processing (luong ngang: Kafka -> Spark -> ML) ----
    box(ax, 3.0, 7.0, 3.6, 2.2, "Apache Kafka", "proc",
        sub="topics:\ngas.raw.sensor\ngas.alert.events")
    box(ax, 8.0, 7.4, 4.6, 1.5, "Spark Structured Streaming", "proc",
        sub="stream_processor.py")
    box(ax, 14.2, 8.25, 5.0, 0.9, "LSTM Forecaster", "proc",
        sub="gas_forecaster.keras → $p_{5\\min}$", fs=10)
    box(ax, 14.2, 7.05, 5.0, 0.9, "PPO RL Controller", "proc",
        sub="ppo_gas_agent.zip → action", fs=10)

    # ---- App ----
    box(ax, 3.0, 10.8, 2.9, 1.4, "InfluxDB", "app", sub="time-series")
    box(ax, 6.2, 10.8, 2.9, 1.4, "PostgreSQL", "app", sub="alerts / actions")
    box(ax, 9.4, 10.8, 3.2, 1.4, "Backend API", "app", sub="Node.js + SSE")
    box(ax, 12.9, 10.8, 2.6, 1.4, "Dashboard", "app", sub="EJS web")
    box(ax, 15.8, 10.8, 2.6, 1.4, "Telegram", "app", sub="Bot")
    box(ax, 18.7, 10.8, 2.4, 1.4, "Grafana", "app", sub="charts")

    # ---- Device -> Comm ----
    arrow(ax, 6.8, 3.1, 8.0, 4.3, "MQTT", (7.0, 3.7))
    arrow(ax, 17.5, 3.1, 16.3, 4.3, "MQTT", (17.4, 3.7))

    # ---- Comm -> Proc ----
    arrow(ax, 8.0, 5.5, 5.2, 7.0, "produce", (6.0, 6.1))
    arrow(ax, 16.3, 5.5, 9.5, 7.4, "produce", (13.2, 6.1))

    # ---- Kafka <-> Spark ----
    arrow(ax, 6.6, 8.45, 8.0, 8.45, "consume", (7.3, 8.78))
    arrow(ax, 8.0, 8.05, 6.6, 8.05, "alert events", (7.3, 7.72),
          color="#a07020")

    # ---- Spark <-> ML ----
    arrow(ax, 12.6, 8.7, 14.2, 8.7, "window", (13.4, 8.95))
    arrow(ax, 14.2, 8.35, 12.6, 8.35, r"$p_{5\min}$", (13.4, 8.12),
          color="#7e3b8e")
    arrow(ax, 12.6, 7.85, 14.2, 7.85, "state", (13.4, 8.10) if False else (13.4, 7.62))
    arrow(ax, 14.2, 7.5, 12.6, 7.5, "action", (13.4, 7.28), color="#a83232")

    # ---- Spark -> DBs (write) : tach ro, it cheo ----
    arrow(ax, 8.6, 8.9, 4.4, 10.8, "write readings", (5.6, 10.0), rad=-0.12)
    arrow(ax, 9.6, 8.9, 7.6, 10.8, "write alerts/actions", (9.4, 10.05),
          rad=-0.1)

    # ---- Kafka alert events -> Backend : dinh tuyen ben trai len ----
    arrow(ax, 3.4, 9.2, 9.6, 10.8, "consume alerts", (5.0, 10.6),
          color="#a07020", rad=0.22)

    # ---- Backend -> Dashboard / Telegram ----
    arrow(ax, 12.6, 11.5, 12.9, 11.5, color="#666")
    arrow(ax, 12.6, 11.15, 15.8, 11.15, color="#666", label="SSE / push",
          lxy=(14.2, 10.92))

    # ---- InfluxDB -> Grafana ----
    arrow(ax, 4.4, 12.2, 18.7, 12.2, label="query", lxy=(11.5, 12.42),
          color="#888", lw=1.0, rad=-0.05)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    print("saved ->", OUT)


if __name__ == "__main__":
    main()
