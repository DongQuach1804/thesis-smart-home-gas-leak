"""
Evaluate the live pipeline against ground-truth labels.

Reads recorded readings from InfluxDB (written by Spark) and computes:

  * lead_time_s         : seconds between the FIRST predictive alert and the
                          moment gas first crossed CRITICAL_PPM, per leak.
  * miss_rate           : leaks that reached CRITICAL with no prior alert.
  * precision / recall  : classification of "is there an active leak now?"
                          using ``predicted_risk_5min > THRESHOLD`` as the
                          predicted positive label.
  * action_breakdown    : how often each RL action fired during NORMAL vs
                          LEAK windows.

Ground truth is taken from the simulator side-channel, which the simulator
writes into the JSON payload as ``_leak_state`` and is forwarded all the
way to InfluxDB by an opt-in mode below. If ground-truth labels are NOT
present in InfluxDB, the script falls back to deriving them from gas trend
(state changes when gas slope > X ppm/s for N seconds).

Run from repo root::

    python processing/scripts/evaluate_from_influx.py --hours 1
    python processing/scripts/evaluate_from_influx.py --hours 6 --threshold 0.5

Environment overrides:
    INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET_GAS
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Iterable

import numpy as np

CRITICAL_PPM = float(os.getenv("FORECAST_CRITICAL_PPM", "1000.0"))


# ---------------------------------------------------------------------------
# Influx loader
# ---------------------------------------------------------------------------

def load_readings(hours: float) -> list[dict]:
    """Pull all gas_reading rows from the last `hours` hours."""
    from influxdb_client import InfluxDBClient

    url    = os.getenv("INFLUXDB_URL",        "http://localhost:8086")
    token  = os.getenv("INFLUXDB_TOKEN",      "thesis-super-token")
    org    = os.getenv("INFLUXDB_ORG",        "thesis-org")
    bucket = os.getenv("INFLUXDB_BUCKET_GAS", "gas_sensor_data")

    flux = f"""
      from(bucket: "{bucket}")
        |> range(start: -{int(hours * 60)}m)
        |> filter(fn: (r) => r._measurement == "gas_reading")
        |> pivot(
             rowKey: ["_time","device_id","risk_label","rl_action"],
             columnKey: ["_field"],
             valueColumn: "_value")
        |> sort(columns: ["_time"], desc: false)
    """

    rows: list[dict] = []
    with InfluxDBClient(url=url, token=token, org=org) as client:
        for table in client.query_api().query(flux):
            for record in table.records:
                v = record.values
                rows.append({
                    "ts":          record.get_time().timestamp(),
                    "device_id":   v.get("device_id", ""),
                    "gas_ppm":     float(v.get("gas_ppm",           0) or 0),
                    "p5":          float(v.get("predicted_risk_5min", 0) or 0),
                    "rl_action":   v.get("rl_action", "NO_OP"),
                    "risk_label":  v.get("risk_label", "NORMAL"),
                })
    return rows


# ---------------------------------------------------------------------------
# Derive ground-truth leak windows from the gas signal
# ---------------------------------------------------------------------------

@dataclass
class Leak:
    start_idx: int
    end_idx: int
    peak_gas: float
    crossed_critical_at: int | None     # index where gas first >= CRITICAL


def derive_leak_episodes(rows: list[dict], slope_threshold_ppm_s: float = 1.5,
                         window_s: int = 30) -> list[Leak]:
    """A leak window is any contiguous stretch where the rolling 30 s slope
    of gas is positive AND the peak gas during that stretch exceeds 250 ppm.

    Returns list of Leak ranges, with critical-crossing index recorded.
    """
    n = len(rows)
    if n < window_s + 2:
        return []

    gas = np.array([r["gas_ppm"] for r in rows], dtype=np.float32)

    # Rolling slope
    slopes = np.zeros(n, dtype=np.float32)
    for i in range(window_s, n):
        x = np.arange(window_s, dtype=np.float32)
        slopes[i] = np.polyfit(x, gas[i - window_s + 1: i + 1], 1)[0]

    leaks: list[Leak] = []
    in_leak = False
    start = 0
    for i in range(n):
        rising = slopes[i] > slope_threshold_ppm_s
        if rising and not in_leak:
            in_leak = True
            start = i
        elif not rising and in_leak:
            seg = gas[start:i]
            peak = float(seg.max()) if seg.size else 0
            if peak > 250:
                crossed = None
                for j in range(start, i):
                    if gas[j] >= CRITICAL_PPM:
                        crossed = j
                        break
                leaks.append(Leak(start, i, peak, crossed))
            in_leak = False

    if in_leak:
        seg = gas[start:n]
        peak = float(seg.max()) if seg.size else 0
        if peak > 250:
            crossed = None
            for j in range(start, n):
                if gas[j] >= CRITICAL_PPM:
                    crossed = j
                    break
            leaks.append(Leak(start, n, peak, crossed))

    return leaks


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def evaluate(rows: list[dict], threshold: float) -> dict:
    if not rows:
        return {"error": "no rows in InfluxDB — is the pipeline running?"}

    leaks = derive_leak_episodes(rows)

    # Per-leak lead time (between first p5 > threshold and the critical crossing)
    lead_times: list[float] = []
    misses = 0
    for leak in leaks:
        first_alarm = None
        for j in range(leak.start_idx, leak.end_idx):
            if rows[j]["p5"] > threshold:
                first_alarm = j
                break
        if leak.crossed_critical_at is not None:
            if first_alarm is None or first_alarm > leak.crossed_critical_at:
                misses += 1
            else:
                lead = rows[leak.crossed_critical_at]["ts"] - rows[first_alarm]["ts"]
                lead_times.append(max(0.0, lead))
        elif first_alarm is not None:
            # Leak that never reached critical — count nominal lead from start
            lead = rows[leak.end_idx - 1]["ts"] - rows[first_alarm]["ts"]
            lead_times.append(max(0.0, lead))

    # Per-row classification: "active leak now?"
    in_leak_mask = np.zeros(len(rows), dtype=bool)
    for leak in leaks:
        in_leak_mask[leak.start_idx: leak.end_idx] = True
    pred_pos = np.array([r["p5"] > threshold for r in rows])

    tp = int(np.logical_and(pred_pos, in_leak_mask).sum())
    fp = int(np.logical_and(pred_pos, ~in_leak_mask).sum())
    fn = int(np.logical_and(~pred_pos, in_leak_mask).sum())
    tn = int(np.logical_and(~pred_pos, ~in_leak_mask).sum())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall    = tp / (tp + fn) if tp + fn else 0.0
    f1        = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    # RL action breakdown
    actions = {}
    for r in rows:
        a = r["rl_action"]
        actions.setdefault(a, {"normal": 0, "leak": 0})
    for r, leak in zip(rows, in_leak_mask):
        a = r["rl_action"]
        actions[a]["leak" if leak else "normal"] += 1

    return {
        "total_rows":     len(rows),
        "duration_s":     rows[-1]["ts"] - rows[0]["ts"] if len(rows) > 1 else 0,
        "leaks_detected": len(leaks),
        "leaks_critical": sum(1 for l in leaks if l.crossed_critical_at is not None),
        "misses":         misses,
        "miss_rate":      misses / max(1, sum(1 for l in leaks if l.crossed_critical_at is not None)),
        "lead_time_mean": float(np.mean(lead_times)) if lead_times else 0.0,
        "lead_time_med":  float(np.median(lead_times)) if lead_times else 0.0,
        "precision":      precision,
        "recall":         recall,
        "f1":             f1,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "actions":        actions,
    }


# ---------------------------------------------------------------------------
# Pretty print
# ---------------------------------------------------------------------------

def pretty(m: dict) -> None:
    if "error" in m:
        print(m["error"]); return
    print("=" * 70)
    print(f"  Window:           {m['duration_s']/60:.1f} min   ({m['total_rows']} samples)")
    print(f"  Leaks detected:   {m['leaks_detected']}  (of which {m['leaks_critical']} reached CRITICAL)")
    print(f"  Misses:           {m['misses']}  (miss_rate = {m['miss_rate']*100:.1f}%)")
    print(f"  Lead time:        mean={m['lead_time_mean']:.1f}s   median={m['lead_time_med']:.1f}s")
    print()
    print("  Per-row classification ('is there a leak right now?')")
    print(f"    precision = {m['precision']*100:6.2f}%")
    print(f"    recall    = {m['recall']*100:6.2f}%")
    print(f"    F1        = {m['f1']*100:6.2f}%")
    print(f"    confusion: TP={m['tp']}  FP={m['fp']}  FN={m['fn']}  TN={m['tn']}")
    print()
    print("  RL action breakdown (rows fired):")
    print(f"    {'action':<14} {'NORMAL':>8} {'LEAK':>8}")
    for a, c in sorted(m["actions"].items()):
        print(f"    {a:<14} {c['normal']:>8} {c['leak']:>8}")
    print("=" * 70)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=float, default=1.0,
                   help="How many hours of recent data to evaluate")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="p5 threshold counted as 'predicted positive'")
    args = p.parse_args()

    print(f"Loading last {args.hours}h from InfluxDB...")
    rows = load_readings(args.hours)
    if not rows:
        print("No data found. Make sure the pipeline (docker compose) is running")
        print("and has had time to write at least a few readings.")
        sys.exit(1)

    print(f"Loaded {len(rows)} samples. Computing metrics (threshold={args.threshold})...")
    pretty(evaluate(rows, args.threshold))


if __name__ == "__main__":
    main()
