from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
THESIS = ROOT / "KLTN_25_2_DuongLV_DongQM_MMTT2022_1 (1)"
EXP = THESIS / "img" / "exp"

BLUE = "#174f91"
MID_BLUE = "#2e7db8"
LIGHT_BLUE = "#eaf2fb"
TEAL = "#2db8c5"
GREEN = "#4f9954"
AMBER = "#efb450"
RED = "#cf2929"
DARK = "#20252b"
GRAY = "#6c737c"
LIGHT_GRAY = "#eef1f4"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    windows = Path("C:/Windows/Fonts")
    candidates = [
        windows / ("arialbd.ttf" if bold else "arial.ttf"),
        windows / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windows / ("calibrib.ttf" if bold else "calibri.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = font(34, True)
FONT_SUBTITLE = font(20)
FONT_AXIS = font(18)
FONT_AXIS_BOLD = font(18, True)
FONT_SMALL = font(15)
FONT_LABEL = font(17)
FONT_LABEL_BOLD = font(17, True)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_center(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, fnt: ImageFont.ImageFont, fill: str = DARK) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((x - w / 2, y - h / 2), text, font=fnt, fill=fill)


def draw_right(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, fnt: ImageFont.ImageFont, fill: str = DARK) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((x - w, y - h / 2), text, font=fnt, fill=fill)


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=16, fill=fill, outline=outline, width=width)


def save(img: Image.Image, name: str) -> None:
    EXP.mkdir(parents=True, exist_ok=True)
    img.save(EXP / name, "PNG")


def nice_max(value: float) -> float:
    if value <= 0:
        return 1
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for mult in (1, 2, 5, 10):
        if value <= mult * base:
            return mult * base
    return 10 * base


def draw_axes(draw: ImageDraw.ImageDraw, plot: tuple[int, int, int, int], y_max: float, ticks: int = 5, y_fmt=lambda v: f"{v:g}") -> None:
    left, top, right, bottom = plot
    draw.line((left, bottom, right, bottom), fill=DARK, width=2)
    draw.line((left, top, left, bottom), fill=DARK, width=2)
    for i in range(ticks + 1):
        value = y_max * i / ticks
        y = bottom - (bottom - top) * i / ticks
        draw.line((left - 6, y, right, y), fill=LIGHT_GRAY if i > 0 else DARK, width=1)
        draw_right(draw, left - 12, y, y_fmt(value), FONT_SMALL, GRAY)


def make_uci_histogram() -> None:
    img = Image.new("RGB", (1500, 860), "white")
    draw = ImageDraw.Draw(img)
    draw_center(draw, 750, 55, "UCI Gas Sensor Array dataset histogram", FONT_TITLE, BLUE)
    draw_center(draw, 750, 94, "Sample count by source file (100 Hz dynamic gas mixtures)", FONT_SUBTITLE, GRAY)

    labels = ["Ethylene-Methane", "Ethylene-CO"]
    values = [4_208_261, 4_178_504]
    y_max = nice_max(max(values))
    plot = (170, 160, 1340, 670)
    draw_axes(draw, plot, y_max, ticks=5, y_fmt=lambda v: f"{v / 1_000_000:.1f}M")

    left, top, right, bottom = plot
    width = 260
    gap = 190
    start = left + 260
    for i, (label, value) in enumerate(zip(labels, values)):
        x0 = start + i * (width + gap)
        x1 = x0 + width
        y = bottom - (bottom - top) * value / y_max
        color = MID_BLUE if i == 0 else TEAL
        draw.rounded_rectangle((x0, y, x1, bottom), radius=12, fill=color)
        draw_center(draw, (x0 + x1) / 2, y - 26, f"{value:,}", FONT_LABEL_BOLD, DARK)
        draw_center(draw, (x0 + x1) / 2, bottom + 34, label, FONT_LABEL_BOLD, DARK)
        draw_center(draw, (x0 + x1) / 2, bottom + 62, "19 attributes", FONT_LABEL, GRAY)

    draw_center(draw, 60, 414, "Samples", FONT_AXIS_BOLD, GRAY)
    rounded_rect(draw, (170, 760, 1340, 835), LIGHT_BLUE, "#c8d9ea")
    draw.text((205, 781), "Use in thesis: reference dataset for time-series gas sensor behavior; not used as runtime training data.", font=FONT_LABEL, fill=DARK)
    save(img, "uci_dataset_histogram.png")


def make_kaggle_histogram() -> None:
    metrics = json.loads((EXP / "lstm_metrics_kaggle.json").read_text(encoding="utf-8"))
    cfg = metrics["config"]
    train_total = int(cfg["n_train"])
    test_total = int(cfg["n_test"])
    train_pos = int(round(train_total * float(cfg["pos_frac_train"])))
    test_pos = int(metrics["tp"] + metrics["fn"])
    train_neg = train_total - train_pos
    test_neg = test_total - test_pos
    raw_rows = 405_184

    img = Image.new("RGB", (1500, 900), "white")
    draw = ImageDraw.Draw(img)
    draw_center(draw, 750, 55, "Kaggle Environmental Sensor histogram", FONT_TITLE, BLUE)
    draw_center(draw, 750, 94, "Time-window labels built from high LPG quantile proxy", FONT_SUBTITLE, GRAY)

    plot = (180, 175, 1345, 665)
    y_max = nice_max(max(train_total, test_total, raw_rows))
    draw_axes(draw, plot, y_max, ticks=5, y_fmt=lambda v: f"{v / 1000:.0f}k")
    left, top, right, bottom = plot

    bars = [
        ("Raw rows", raw_rows, 0, "#9db6d8", ""),
        ("Train windows", train_neg, train_pos, MID_BLUE, f"+ {train_pos:,} positive"),
        ("Test windows", test_neg, test_pos, TEAL, f"+ {test_pos:,} positive"),
    ]
    width = 225
    gap = 135
    start = left + 190
    for i, (label, neg, pos, color, note) in enumerate(bars):
        x0 = start + i * (width + gap)
        x1 = x0 + width
        y0 = bottom - (bottom - top) * neg / y_max
        draw.rounded_rectangle((x0, y0, x1, bottom), radius=12, fill=color)
        if pos:
            y_pos = bottom - (bottom - top) * (neg + pos) / y_max
            draw.rounded_rectangle((x0, y_pos, x1, y0), radius=12, fill=AMBER)
            draw_center(draw, (x0 + x1) / 2, y_pos - 26, f"{neg + pos:,}", FONT_LABEL_BOLD, DARK)
        else:
            draw_center(draw, (x0 + x1) / 2, y0 - 26, f"{neg:,}", FONT_LABEL_BOLD, DARK)
        draw_center(draw, (x0 + x1) / 2, bottom + 34, label, FONT_LABEL_BOLD, DARK)
        if note:
            draw_center(draw, (x0 + x1) / 2, bottom + 62, note, FONT_SMALL, GRAY)

    draw_center(draw, 74, 420, "Records / windows", FONT_AXIS_BOLD, GRAY)
    draw.rounded_rectangle((1030, 190, 1320, 295), radius=14, fill="white", outline="#d4dce5", width=2)
    draw.rectangle((1058, 215, 1090, 239), fill=MID_BLUE)
    draw.text((1106, 210), "Negative event windows", font=FONT_SMALL, fill=DARK)
    draw.rectangle((1058, 255, 1090, 279), fill=AMBER)
    draw.text((1106, 250), "Positive event windows", font=FONT_SMALL, fill=DARK)

    rounded_rect(draw, (180, 750, 1345, 832), LIGHT_BLUE, "#c8d9ea")
    draw.text((212, 772), f"Attributes: 9 | LPG threshold proxy: {cfg['lpg_threshold_value']:.6f} | Test positive rate: {cfg['pos_frac_test'] * 100:.2f}%", font=FONT_LABEL, fill=DARK)
    save(img, "kaggle_dataset_histogram.png")


def read_history() -> list[dict[str, float]]:
    with (EXP / "lstm_history.csv").open("r", encoding="utf-8", newline="") as f:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]


def draw_line_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    xs: list[float],
    series: list[tuple[str, list[float], str]],
    y_min: float | None = None,
    y_max: float | None = None,
) -> None:
    left, top, right, bottom = box
    rounded_rect(draw, (left, top, right, bottom), "white", "#d9e1ea", 2)
    draw.text((left + 18, top + 14), title, font=FONT_LABEL_BOLD, fill=DARK)
    plot = (left + 70, top + 65, right - 25, bottom - 54)
    values = [v for _, ys, _ in series for v in ys]
    if y_min is None:
        y_min = min(values)
    if y_max is None:
        y_max = max(values)
    pad = max((y_max - y_min) * 0.08, 0.02)
    y_min = max(0, y_min - pad)
    y_max = min(1.0 if y_max <= 1.0 else y_max + pad, y_max + pad)
    if y_max <= y_min:
        y_max = y_min + 1
    pleft, ptop, pright, pbottom = plot
    draw.rectangle((pleft, ptop, pright, pbottom), outline="#eef1f4")
    for i in range(5):
        y = pbottom - (pbottom - ptop) * i / 4
        draw.line((pleft, y, pright, y), fill=LIGHT_GRAY, width=1)
        val = y_min + (y_max - y_min) * i / 4
        draw_right(draw, pleft - 9, y, f"{val:.2f}", FONT_SMALL, GRAY)
    draw.line((pleft, pbottom, pright, pbottom), fill=DARK, width=2)
    draw.line((pleft, ptop, pleft, pbottom), fill=DARK, width=2)

    x_min, x_max = min(xs), max(xs)
    for name, ys, color in series:
        pts = []
        for x, yv in zip(xs, ys):
            px = pleft + (pright - pleft) * (x - x_min) / (x_max - x_min)
            py = pbottom - (pbottom - ptop) * (yv - y_min) / (y_max - y_min)
            pts.append((px, py))
        draw.line(pts, fill=color, width=4, joint="curve")
        for px, py in pts[:: max(1, len(pts) // 8)]:
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=color)

    legend_x = left + 20
    legend_y = bottom - 35
    for name, _, color in series:
        draw.line((legend_x, legend_y, legend_x + 28, legend_y), fill=color, width=5)
        draw.text((legend_x + 36, legend_y - 9), name, font=FONT_SMALL, fill=GRAY)
        legend_x += 170


def make_epoch_metrics() -> None:
    hist = read_history()
    xs = [row["epoch"] for row in hist]
    img = Image.new("RGB", (1700, 1100), "white")
    draw = ImageDraw.Draw(img)
    draw_center(draw, 850, 58, "LSTM training metrics by epoch", FONT_TITLE, BLUE)
    draw_center(draw, 850, 98, "Trace simulation: 20 epochs, time-ordered train/validation split", FONT_SUBTITLE, GRAY)

    panels = [
        ((70, 145, 820, 555), "Binary cross-entropy loss", [("train", [r["loss"] for r in hist], MID_BLUE), ("val", [r["val_loss"] for r in hist], AMBER)]),
        ((880, 145, 1630, 555), "Accuracy", [("train", [r["accuracy"] for r in hist], MID_BLUE), ("val", [r["val_accuracy"] for r in hist], AMBER)]),
        ((70, 610, 820, 1020), "Precision", [("train", [r["precision"] for r in hist], MID_BLUE), ("val", [r["val_precision"] for r in hist], AMBER)]),
        ((880, 610, 1630, 1020), "Recall", [("train", [r["recall"] for r in hist], MID_BLUE), ("val", [r["val_recall"] for r in hist], AMBER)]),
    ]
    for box, title, series in panels:
        draw_line_panel(draw, box, title, xs, series)
    save(img, "lstm_epoch_metrics.png")


def make_mae_rmse() -> None:
    sim = json.loads((EXP / "lstm_metrics.json").read_text(encoding="utf-8"))
    kaggle = json.loads((EXP / "lstm_metrics_kaggle.json").read_text(encoding="utf-8"))

    def calc(m: dict) -> dict[str, float]:
        total = m["tp"] + m["tn"] + m["fp"] + m["fn"]
        errors = m["fp"] + m["fn"]
        mae = errors / total
        rmse = math.sqrt(errors / total)
        return {"total": total, "errors": errors, "mae": mae, "rmse": rmse}

    rows = {
        "Simulation": calc(sim),
        "Kaggle": calc(kaggle),
    }
    (EXP / "lstm_mae_rmse.json").write_text(
        json.dumps(
            {
                "definition": "MAE and RMSE computed on thresholded binary event forecasts.",
                "note": "These are not ppm regression errors because the current LSTM outputs event risk probability, not future gas_ppm.",
                "results": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    img = Image.new("RGB", (1500, 860), "white")
    draw = ImageDraw.Draw(img)
    draw_center(draw, 750, 55, "LSTM event forecast error", FONT_TITLE, BLUE)
    draw_center(draw, 750, 94, "MAE/RMSE over binary future-event decisions after thresholding", FONT_SUBTITLE, GRAY)

    plot = (180, 165, 1340, 660)
    y_max = 0.35
    draw_axes(draw, plot, y_max, ticks=7, y_fmt=lambda v: f"{v:.2f}")
    left, top, right, bottom = plot
    group_centers = [520, 980]
    bar_w = 110
    for cx, (name, data) in zip(group_centers, rows.items()):
        for offset, metric, color in [(-70, "mae", MID_BLUE), (70, "rmse", AMBER)]:
            x0 = cx + offset - bar_w / 2
            x1 = cx + offset + bar_w / 2
            value = data[metric]
            y = bottom - (bottom - top) * value / y_max
            draw.rounded_rectangle((x0, y, x1, bottom), radius=12, fill=color)
            draw_center(draw, cx + offset, y - 25, f"{value:.3f}", FONT_LABEL_BOLD, DARK)
        draw_center(draw, cx, bottom + 38, name, FONT_LABEL_BOLD, DARK)
        draw_center(draw, cx, bottom + 66, f"errors: {data['errors']:,}/{data['total']:,}", FONT_SMALL, GRAY)

    draw_center(draw, 70, 415, "Error", FONT_AXIS_BOLD, GRAY)
    draw.rounded_rectangle((1050, 190, 1305, 290), radius=14, fill="white", outline="#d4dce5", width=2)
    draw.rectangle((1080, 215, 1112, 239), fill=MID_BLUE)
    draw.text((1128, 210), "MAE", font=FONT_SMALL, fill=DARK)
    draw.rectangle((1080, 255, 1112, 279), fill=AMBER)
    draw.text((1128, 250), "RMSE", font=FONT_SMALL, fill=DARK)

    rounded_rect(draw, (180, 735, 1340, 812), LIGHT_BLUE, "#c8d9ea")
    draw.text((212, 756), "For direct gas_ppm regression, MAE/RMSE would need a different LSTM output target.", font=FONT_LABEL, fill=DARK)
    save(img, "lstm_mae_rmse.png")


def main() -> None:
    make_uci_histogram()
    make_kaggle_histogram()
    make_epoch_metrics()
    make_mae_rmse()
    print("Generated Ch4 feedback figures in", EXP)


if __name__ == "__main__":
    main()
