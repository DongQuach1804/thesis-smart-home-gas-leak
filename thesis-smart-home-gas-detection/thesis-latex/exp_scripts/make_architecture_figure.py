"""Generate the 4-layer system architecture diagram (cleaner v2 layout).

Compared to v1:
  - Underscores are written as plain text (matplotlib default text mode)
    so they render correctly instead of showing a literal backslash.
  - Arrows between Spark / Kafka / databases / Backend are spread out
    horizontally so labels stop overlapping in the middle of the page.

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

LAYER_FILL = {
    "device": ("#fef3e6", "#e8a25b"),
    "comm":   ("#e6f4ea", "#5ba26c"),
    "proc":   ("#e7eef8", "#4a6fa5"),
    "app":    ("#fae7e7", "#b35b5b"),
}
TEXT_DARK = "#1f2d3d"


def box(ax, x, y, w, h, text, layer_key, fontsize=11, sub_text=None):
    fill, border = LAYER_FILL[layer_key]
    b = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.18,rounding_size=0.18",
        linewidth=1.6, edgecolor=border, facecolor=fill,
    )
    ax.add_patch(b)
    if sub_text:
        ax.text(x + w / 2, y + h * 0.64, text,
                ha="center", va="center", fontsize=fontsize,
                weight="bold", color=TEXT_DARK)
        ax.text(x + w / 2, y + h * 0.30, sub_text,
                ha="center", va="center", fontsize=fontsize - 2,
                color="#4a5566")
    else:
        ax.text(x + w / 2, y + h / 2, text,
                ha="center", va="center", fontsize=fontsize,
                weight="bold", color=TEXT_DARK)


def layer_band(ax, y, h, label, sub_label, layer_key,
               x_left=2.6, x_right=21.4):
    fill, border = LAYER_FILL[layer_key]
    ax.add_patch(plt.Rectangle(
        (x_left, y), x_right - x_left, h,
        facecolor=fill, alpha=0.28, edgecolor=border, linewidth=1.0,
    ))
    ax.text(0.6, y + h * 0.62, label,
            ha="left", va="center", fontsize=13.5,
            weight="bold", color=border)
    ax.text(0.6, y + h * 0.28, sub_label,
            ha="left", va="center", fontsize=9.5,
            style="italic", color="#666666")


def arrow(ax, x1, y1, x2, y2, label=None, label_xy=None,
          color="#34495e", lw=1.5, style="-|>", rad=0.0):
    cs = f"arc3,rad={rad}" if rad else None
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=14, linewidth=lw, color=color,
        connectionstyle=cs,
    )
    ax.add_patch(a)
    if label and label_xy:
        ax.text(label_xy[0], label_xy[1], label,
                ha="center", va="center", fontsize=9.5, color=color,
                bbox=dict(boxstyle="round,pad=0.22",
                          facecolor="white",
                          edgecolor="#d0d0d0", linewidth=0.6, alpha=0.96))


def main() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"

    fig, ax = plt.subplots(figsize=(18, 11))
    ax.set_xlim(0, 21.6)
    ax.set_ylim(0, 13.5)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(11.0, 13.0,
            "Kiến trúc hệ thống 4 tầng",
            ha="center", va="center", fontsize=17, weight="bold",
            color=TEXT_DARK)

    # ---------- Layer bands ----------
    layer_band(ax, 10.4, 2.0, "Ứng dụng",  "Frontend, API, alerts", "app")
    layer_band(ax, 6.4,  3.4, "Xử lý",     "Streaming + ML inference", "proc")
    layer_band(ax, 4.0,  1.8, "Truyền thông", "MQTT / Kafka",        "comm")
    layer_band(ax, 1.4,  2.0, "Thiết bị",  "Sensors + simulator",   "device")

    # ---------- Device layer ----------
    box(ax, 4.5, 1.7, 4.2, 1.4,
        "ESP32 + MQ-2/DHT22", "device",
        sub_text="C++/Arduino, 1 Hz publish")
    box(ax, 9.5, 1.7, 4.6, 1.4,
        "Sensor Simulator", "device",
        sub_text="Python — physical state machine")
    box(ax, 15.0, 1.7, 4.4, 1.4,
        "MQTT publish", "device",
        sub_text="topic: sensors/gas")

    # ---------- Communication layer ----------
    box(ax, 5.5, 4.30, 5.0, 1.2,
        "Mosquitto Broker", "comm",
        sub_text="port 1883, persistence on")
    box(ax, 12.5, 4.30, 6.2, 1.2,
        "mqtt_kafka_bridge", "comm",
        sub_text="transcode MQTT → Kafka")

    # ---------- Processing layer ----------
    box(ax, 3.0, 7.1, 3.6, 2.0,
        "Apache Kafka", "proc",
        sub_text="topics:\ngas.raw.sensor\ngas.alert.events")
    box(ax, 7.5, 7.6, 4.4, 1.5,
        "Spark Structured Streaming", "proc",
        sub_text="stream_processor.py")
    box(ax, 13.0, 8.4, 4.8, 0.85,
        "LSTM Forecaster", "proc",
        sub_text="gas_forecaster.keras  →  p_{5min}", fontsize=10)
    box(ax, 13.0, 7.15, 4.8, 0.85,
        "PPO RL Controller", "proc",
        sub_text="ppo_gas_agent.zip  →  action", fontsize=10)

    # ---------- Application layer ----------
    box(ax, 3.0, 10.65, 2.8, 1.4,
        "InfluxDB", "app", sub_text="time-series")
    box(ax, 6.1, 10.65, 2.8, 1.4,
        "PostgreSQL", "app", sub_text="alerts / actions")
    box(ax, 9.2, 10.65, 3.4, 1.4,
        "Backend API", "app",
        sub_text="Node.js + SSE")
    box(ax, 12.9, 10.65, 2.4, 1.4,
        "Dashboard", "app", sub_text="EJS web")
    box(ax, 15.6, 10.65, 2.4, 1.4,
        "Telegram", "app", sub_text="Bot")
    box(ax, 18.3, 10.65, 2.0, 1.4,
        "Grafana", "app", sub_text="charts")

    # ---------- Vertical arrows: Device → Comm ----------
    arrow(ax, 6.6, 3.1, 8.0, 4.30, "MQTT", (7.0, 3.70))
    arrow(ax, 17.2, 3.1, 15.6, 4.30, "MQTT", (16.85, 3.70))

    # ---------- Comm → Proc ----------
    arrow(ax, 8.0, 5.5, 5.0, 7.1, "produce", (6.10, 6.05))
    arrow(ax, 15.6, 5.5, 9.5, 7.6, "produce", (13.0, 6.05))

    # ---------- Kafka ↔ Spark ----------
    arrow(ax, 6.6, 8.30, 7.5, 8.30, "consume", (7.05, 8.62))
    arrow(ax, 7.5, 7.95, 6.6, 7.95,
          "alert events", (7.05, 7.62), color="#a07020")

    # ---------- Spark ↔ LSTM ----------
    arrow(ax, 11.9, 8.95, 13.0, 8.95, "window", (12.45, 9.20))
    arrow(ax, 13.0, 8.60, 11.9, 8.60,
          r"$p_{5\min}$", (12.45, 8.36), color="#7e3b8e")

    # ---------- Spark ↔ PPO ----------
    arrow(ax, 11.9, 7.85, 13.0, 7.85, "state", (12.45, 8.10))
    arrow(ax, 13.0, 7.45, 11.9, 7.45,
          "action", (12.45, 7.20), color="#a83232")

    # ---------- Storage writes (Spark → DBs) ----------
    arrow(ax, 8.0, 9.1, 4.4, 10.65,
          "write readings", (5.9, 9.95))
    arrow(ax, 9.0, 9.1, 7.5, 10.65,
          "write alerts/actions", (8.55, 9.95))

    # ---------- Kafka alerts → Backend (clearly separated) ----------
    arrow(ax, 4.8, 9.10, 10.9, 10.65,
          "consume alerts", (8.0, 9.85), color="#a07020", rad=0.18)

    # ---------- Backend → Dashboard / Telegram ----------
    arrow(ax, 12.6, 11.35, 12.9, 11.35, color="#666666")
    arrow(ax, 12.6, 11.05, 15.6, 11.05, color="#666666",
          label="SSE / push", label_xy=(14.1, 10.78))

    # ---------- InfluxDB → Grafana ----------
    arrow(ax, 4.4, 12.10, 18.3, 12.10,
          label="query", label_xy=(11.5, 12.32),
          color="#888888", lw=1.0, rad=-0.06)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160, bbox_inches="tight", facecolor="white")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
