"""
Scientific evaluation: compare three controllers on the simulator.

Two-pass methodology
--------------------
Pass 1 (ORACLE): same seed, NO controller actions. Record for each leak
    episode the *natural critical time* — the moment gas would have hit
    CRITICAL_PPM if nobody intervened.

Pass 2 (CONTROLLER): same seed, the controller acts each step. Record for
    each leak the time of the FIRST non-NO_OP action.

Lead time per leak = natural_critical_time - first_action_time

Because pass 1 and pass 2 share the same RNG seed, leaks start at the same
real-time index, so the comparison is apples-to-apples.

Metrics reported
----------------
* lead_time_s          mean lead time across all leaks that ORACLE pass
                       confirms would have reached critical
* miss_rate            fraction of would-be-critical leaks where the
                       controller never acted
* alarms_per_hour      number of distinct alarm EVENTS (separated by ≥60s
                       of silence) during NORMAL state, normalised to /hour
* mean_peak_gas        avg peak gas during leak episodes (lower = better
                       mitigation; only RL can reduce this)

Run::

    python processing/scripts/benchmark.py --hours 6 --seed 42
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from device.simulator.sensor_simulator import (   # noqa: E402
    State, World, STEP_FN, _maybe_transition,
)
from processing.ml.inference.forecaster_inference import GasForecaster   # noqa: E402
from processing.ml.inference.rl_inference import GasResponseAgent        # noqa: E402

CRITICAL = 1000.0
ALARM_GAP_S = 60     # alarms within this window count as one event


@dataclass
class Stats:
    name: str
    leaks_total: int = 0
    leaks_oracle_critical: int = 0
    misses: int = 0
    lead_times: list[float] = field(default_factory=list)
    alarm_events: int = 0
    normal_seconds: int = 0
    leak_peak_gas: list[float] = field(default_factory=list)

    def report(self) -> dict:
        oracle = max(1, self.leaks_oracle_critical)
        return {
            "controller":       self.name,
            "leaks":            self.leaks_total,
            "oracle_critical":  self.leaks_oracle_critical,
            "lead_time_s":      round(float(np.mean(self.lead_times)) if self.lead_times else 0.0, 1),
            "lead_time_med":    round(float(np.median(self.lead_times)) if self.lead_times else 0.0, 1),
            "miss_rate":        round(self.misses / oracle, 3),
            "alarms_per_hour":  round(self.alarm_events / max(1, self.normal_seconds / 3600.0), 2),
            "mean_peak_gas":    round(float(np.mean(self.leak_peak_gas)) if self.leak_peak_gas else 0.0, 1),
        }


# ---------------------------------------------------------------------------
# Pass 1: Oracle simulation (no controller acts)
# ---------------------------------------------------------------------------

def run_oracle(hours: float, seed: int) -> dict:
    """Replay simulator without intervention. Returns dict mapping
    leak_id -> {start_t, natural_critical_t (or None)}."""
    import random
    random.seed(seed)
    np.random.seed(seed)

    n = int(hours * 3600)
    world = World()
    leaks: dict[int, dict] = {}
    leak_id = -1
    in_leak = False

    for t in range(n):
        STEP_FN[world.state](world, 1.0)
        _maybe_transition(world, 1.0)
        world.state_age_s += 1.0

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            leak_id += 1
            leaks[leak_id] = {"start_t": t, "natural_critical_t": None, "end_t": None}
            in_leak = True
        elif in_leak:
            if world.gas >= CRITICAL and leaks[leak_id]["natural_critical_t"] is None:
                leaks[leak_id]["natural_critical_t"] = t
            if not leaking:
                leaks[leak_id]["end_t"] = t
                in_leak = False

    if in_leak:
        leaks[leak_id]["end_t"] = n
    return leaks


# ---------------------------------------------------------------------------
# Pass 2: Controller simulation
# ---------------------------------------------------------------------------

def run_controller(controller: str, hours: float, seed: int,
                   oracle: dict, forecaster: GasForecaster,
                   rl_agent: GasResponseAgent) -> Stats:
    import random
    random.seed(seed)
    np.random.seed(seed)

    stats = Stats(controller)
    n = int(hours * 3600)
    world = World()

    in_leak = False
    leak_id = -1
    leak_first_action_t = -1
    leak_peak = 0.0
    fan_on = False
    valve_closed = False

    last_alarm_t = -1_000_000
    _last_p5 = 0.0

    for t in range(n):
        STEP_FN[world.state](world, 1.0)
        if fan_on and world.state != State.VENTILATING:
            world.gas = max(50.0, world.gas * 0.985)
        _maybe_transition(world, 1.0)
        world.state_age_s += 1.0

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            in_leak = True
            leak_id += 1
            stats.leaks_total += 1
            leak_first_action_t = -1
            leak_peak = world.gas
            if leak_id in oracle and oracle[leak_id]["natural_critical_t"] is not None:
                stats.leaks_oracle_critical += 1
        elif in_leak:
            leak_peak = max(leak_peak, world.gas)
            if not leaking:
                stats.leak_peak_gas.append(leak_peak)
                # Was this a leak that ORACLE says would have reached critical?
                if (leak_id in oracle
                        and oracle[leak_id]["natural_critical_t"] is not None
                        and leak_first_action_t < 0):
                    stats.misses += 1
                in_leak = False
                fan_on = False
                valve_closed = False
        else:
            stats.normal_seconds += 1

        # Choose action — only call TF when the controller actually needs p5
        if controller == "threshold":
            action = 1 if world.gas > 800 else 0
        elif controller == "forecaster":
            # Predict every 5 s (matches real pipeline cadence; saves 5x TF calls)
            if t % 5 == 0:
                _last_p5 = forecaster.predict("bench", world.gas, world.temp, world.hum)
            action = 1 if _last_p5 > 0.5 else 0
        elif controller == "rl":
            if t % 5 == 0:
                _last_p5 = forecaster.predict("bench", world.gas, world.temp, world.hum)
            a, _ = rl_agent.choose("bench", world.gas, world.temp, world.hum, _last_p5)
            action = a
        else:
            raise ValueError(controller)

        if action == 0:
            continue

        # Track first action of this leak (for lead-time)
        if in_leak and leak_first_action_t < 0:
            leak_first_action_t = t
            if leak_id in oracle:
                natural_t = oracle[leak_id]["natural_critical_t"]
                if natural_t is not None:
                    lead = natural_t - t
                    if lead >= 0:
                        stats.lead_times.append(float(lead))
                    # else: alarm came AFTER the would-be critical -> count as miss
                    else:
                        stats.misses += 1

        # Distinct alarm events during NORMAL
        if not in_leak and (t - last_alarm_t) > ALARM_GAP_S:
            stats.alarm_events += 1
            last_alarm_t = t
        elif not in_leak:
            last_alarm_t = t

        # Apply mitigation actions
        if action == 2:
            fan_on = True
        elif action == 3 and in_leak:
            valve_closed = True
            world.state = State.VENTILATING
            world.state_age_s = 0.0

    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=6.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=int, default=1,
                        help="If >1, run with --seed, --seed+1, ... and report mean +/- std")
    args = parser.parse_args()

    forecaster = GasForecaster()
    rl_agent = GasResponseAgent()

    all_results: dict[str, list[dict]] = {"threshold": [], "forecaster": [], "rl": []}

    for s in range(args.seeds):
        seed = args.seed + s
        print(f"\n# seed={seed}: running ORACLE pass...")
        oracle = run_oracle(args.hours, seed)
        n_oracle_critical = sum(1 for v in oracle.values()
                                if v["natural_critical_t"] is not None)
        print(f"  oracle: {len(oracle)} leaks total, "
              f"{n_oracle_critical} would have reached CRITICAL.")

        for ctrl in ("threshold", "forecaster", "rl"):
            print(f"  running CONTROLLER pass: {ctrl}...")
            s_obj = run_controller(ctrl, args.hours, seed, oracle, forecaster, rl_agent)
            all_results[ctrl].append(s_obj.report())

    # ── Aggregate ─────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    headers = ["controller", "leaks", "lead_s", "lead_med", "miss%", "alarm/hr", "peak_gas"]
    print(f"{headers[0]:<12} {headers[1]:>6} {headers[2]:>10} {headers[3]:>10} "
          f"{headers[4]:>8} {headers[5]:>10} {headers[6]:>10}")
    print("-" * 100)
    for ctrl, runs in all_results.items():
        if args.seeds == 1:
            r = runs[0]
            print(f"{r['controller']:<12} {r['leaks']:>6} {r['lead_time_s']:>10.1f} "
                  f"{r['lead_time_med']:>10.1f} {r['miss_rate']*100:>7.1f}% "
                  f"{r['alarms_per_hour']:>10.2f} {r['mean_peak_gas']:>10.1f}")
        else:
            def stat(key):
                vals = [r[key] for r in runs]
                return float(np.mean(vals)), float(np.std(vals))
            ls_m, ls_s = stat("lead_time_s")
            mr_m, mr_s = stat("miss_rate")
            ah_m, ah_s = stat("alarms_per_hour")
            pg_m, pg_s = stat("mean_peak_gas")
            n_leaks    = int(np.mean([r["leaks"] for r in runs]))
            print(f"{ctrl:<12} {n_leaks:>6} {ls_m:>6.0f}±{ls_s:<3.0f} "
                  f"{'':>10} {mr_m*100:>5.1f}±{mr_s*100:<2.1f}% "
                  f"{ah_m:>5.1f}±{ah_s:<3.1f} {pg_m:>6.0f}±{pg_s:<3.0f}")
    print("=" * 100)
    print("Lead times measured against the ORACLE replay (same seed, no intervention).")
    print("Higher lead_s = earlier warning; lower miss% & peak_gas = better mitigation.\n")


if __name__ == "__main__":
    main()
