"""Per-scenario benchmark for the three controllers.

Three scenarios are evaluated:

  TC-Idle  : NORMAL-only, no leak ever.        Metric of interest: alarm/hr
  TC-Slow  : Forced single LEAK_SLOW at t=600. Metric: lead_time, miss, peak
  TC-Fast  : Forced single LEAK_FAST at t=600. Metric: lead_time, miss, peak

Each run is 1 hour of simulated time. Stochastic transitions in the simulator
are disabled (SIM_LEAK_PROB_PER_MIN=0) and we drive the state machine
ourselves so the leak happens at a deterministic moment.

Run::

    python processing/scripts/benchmark_scenarios.py --seeds 3

Outputs JSON to thesis-latex/img/exp/scenarios_results.json plus a printed
table.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Force deterministic simulator transitions BEFORE importing the module
os.environ["SIM_LEAK_PROB_PER_MIN"] = "0"

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from device.simulator.sensor_simulator import State, World, STEP_FN   # noqa: E402
from processing.ml.inference.forecaster_inference import GasForecaster  # noqa: E402
from processing.ml.inference.rl_inference import GasResponseAgent       # noqa: E402

CRITICAL = 1000.0
ALARM_GAP_S = 60
EPISODE_SECONDS = 3600     # 1 hour
LEAK_TRIGGER_T = 600       # leak starts 10 minutes in
LEAK_AUTORESOLVE_AGE = 240 # leak auto-resolves after 4 minutes if no action


# ---------------------------------------------------------------------------
# Scenario transition functions
# ---------------------------------------------------------------------------

def _transition_idle(world: World, t: int) -> None:
    """No leak, ever. World stays in NORMAL."""
    pass


def _transition_single_slow(world: World, t: int) -> None:
    if t == LEAK_TRIGGER_T and world.state == State.NORMAL:
        world.state = State.LEAK_SLOW
        world.state_age_s = 0.0
        return
    _self_resolve(world)


def _transition_single_fast(world: World, t: int) -> None:
    if t == LEAK_TRIGGER_T and world.state == State.NORMAL:
        world.state = State.LEAK_FAST
        world.state_age_s = 0.0
        return
    _self_resolve(world)


def _self_resolve(world: World) -> None:
    """Same self-resolve logic as the stochastic simulator, but deterministic."""
    if world.state in (State.LEAK_SLOW, State.LEAK_FAST):
        if world.state_age_s > LEAK_AUTORESOLVE_AGE:
            world.state = State.VENTILATING
            world.state_age_s = 0.0
    elif world.state == State.VENTILATING:
        if world.gas < 100 and world.state_age_s > 30:
            world.state = State.NORMAL
            world.state_age_s = 0.0


SCENARIOS = {
    "idle": _transition_idle,
    "slow": _transition_single_slow,
    "fast": _transition_single_fast,
}


# ---------------------------------------------------------------------------
# Statistics container
# ---------------------------------------------------------------------------

@dataclass
class Stats:
    controller: str
    scenario: str
    leaks_total: int = 0
    leaks_oracle_critical: int = 0
    misses: int = 0
    lead_times: list[float] = field(default_factory=list)
    alarm_events: int = 0
    normal_seconds: int = 0
    leak_peak_gas: list[float] = field(default_factory=list)

    def summary(self) -> dict:
        oracle = max(1, self.leaks_oracle_critical)
        return {
            "controller": self.controller,
            "scenario": self.scenario,
            "leaks_total": self.leaks_total,
            "leaks_oracle_critical": self.leaks_oracle_critical,
            "lead_time_s": (
                round(float(np.mean(self.lead_times)), 1) if self.lead_times else 0.0
            ),
            "miss_rate": round(self.misses / oracle, 3),
            "alarms_per_hour": round(
                self.alarm_events / max(1, self.normal_seconds / 3600.0), 2
            ),
            "mean_peak_gas": (
                round(float(np.mean(self.leak_peak_gas)), 1)
                if self.leak_peak_gas else 0.0
            ),
        }


# ---------------------------------------------------------------------------
# Oracle pass
# ---------------------------------------------------------------------------

def run_oracle(scenario: str, seed: int) -> dict:
    import random
    random.seed(seed)
    np.random.seed(seed)
    transition = SCENARIOS[scenario]

    world = World()
    leaks: dict[int, dict] = {}
    leak_id = -1
    in_leak = False

    for t in range(EPISODE_SECONDS):
        STEP_FN[world.state](world, 1.0)
        transition(world, t)
        world.state_age_s += 1.0

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            leak_id += 1
            leaks[leak_id] = {"start_t": t, "natural_critical_t": None, "end_t": None}
            in_leak = True
        elif in_leak:
            if (world.gas >= CRITICAL
                    and leaks[leak_id]["natural_critical_t"] is None):
                leaks[leak_id]["natural_critical_t"] = t
            if not leaking:
                leaks[leak_id]["end_t"] = t
                in_leak = False

    if in_leak:
        leaks[leak_id]["end_t"] = EPISODE_SECONDS
    return leaks


# ---------------------------------------------------------------------------
# Controller pass
# ---------------------------------------------------------------------------

def run_controller(controller: str, scenario: str, seed: int, oracle: dict,
                   forecaster: GasForecaster,
                   rl_agent: GasResponseAgent) -> Stats:
    import random
    random.seed(seed)
    np.random.seed(seed)

    transition = SCENARIOS[scenario]
    stats = Stats(controller=controller, scenario=scenario)
    world = World()

    in_leak = False
    leak_id = -1
    leak_first_action_t = -1
    leak_peak = 0.0
    fan_on = False
    valve_closed = False
    last_alarm_t = -1_000_000
    _last_p5 = 0.0

    for t in range(EPISODE_SECONDS):
        STEP_FN[world.state](world, 1.0)
        if fan_on and world.state != State.VENTILATING:
            world.gas = max(50.0, world.gas * 0.985)
        transition(world, t)
        world.state_age_s += 1.0

        leaking = world.state in (State.LEAK_SLOW, State.LEAK_FAST)
        if leaking and not in_leak:
            in_leak = True
            leak_id += 1
            stats.leaks_total += 1
            leak_first_action_t = -1
            leak_peak = world.gas
            if (leak_id in oracle
                    and oracle[leak_id]["natural_critical_t"] is not None):
                stats.leaks_oracle_critical += 1
        elif in_leak:
            leak_peak = max(leak_peak, world.gas)
            if not leaking:
                stats.leak_peak_gas.append(leak_peak)
                if (leak_id in oracle
                        and oracle[leak_id]["natural_critical_t"] is not None
                        and leak_first_action_t < 0):
                    stats.misses += 1
                in_leak = False
                fan_on = False
                valve_closed = False
        else:
            stats.normal_seconds += 1

        # Choose action
        if controller == "threshold":
            action = 1 if world.gas > 800 else 0
        elif controller == "forecaster":
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

        # First action of this leak
        if in_leak and leak_first_action_t < 0:
            leak_first_action_t = t
            if leak_id in oracle:
                natural_t = oracle[leak_id]["natural_critical_t"]
                if natural_t is not None:
                    lead = natural_t - t
                    if lead >= 0:
                        stats.lead_times.append(float(lead))
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

def aggregate(runs: list[dict]) -> dict:
    """Aggregate per-seed summaries into mean ± std."""
    keys = ("lead_time_s", "miss_rate", "alarms_per_hour", "mean_peak_gas")
    agg = {"controller": runs[0]["controller"], "scenario": runs[0]["scenario"]}
    for k in keys:
        vals = [r[k] for r in runs]
        agg[f"{k}_mean"] = round(float(np.mean(vals)), 2)
        agg[f"{k}_std"] = round(float(np.std(vals)), 2)
    agg["leaks_total_mean"] = float(np.mean([r["leaks_total"] for r in runs]))
    return agg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--out", type=str,
                        default=str(ROOT / "thesis-latex" / "img" / "exp"
                                    / "scenarios_results.json"))
    args = parser.parse_args()

    forecaster = GasForecaster()
    rl_agent = GasResponseAgent()

    all_runs: list[dict] = []

    for scenario in SCENARIOS:
        print(f"\n=== Scenario: {scenario} ===")
        for s in range(args.seeds):
            seed = args.seed_start + s
            print(f"  seed={seed}: running oracle ...")
            oracle = run_oracle(scenario, seed)
            n_critical = sum(
                1 for v in oracle.values() if v["natural_critical_t"] is not None
            )
            print(f"    oracle: {len(oracle)} leak(s), "
                  f"{n_critical} would have reached CRITICAL.")

            for ctrl in ("threshold", "forecaster", "rl"):
                print(f"    controller={ctrl} ...")
                s_obj = run_controller(ctrl, scenario, seed, oracle,
                                       forecaster, rl_agent)
                summary = s_obj.summary()
                summary["seed"] = seed
                all_runs.append(summary)

    # Aggregate
    aggregated = []
    for scenario in SCENARIOS:
        for ctrl in ("threshold", "forecaster", "rl"):
            seed_runs = [r for r in all_runs
                         if r["scenario"] == scenario and r["controller"] == ctrl]
            aggregated.append(aggregate(seed_runs))

    out = Path(args.out)
    out.write_text(json.dumps(
        {"runs": all_runs, "aggregated": aggregated}, indent=2
    ))
    print(f"\nSaved -> {out}")

    # Print table
    print("\n" + "=" * 100)
    print(f"{'Scenario':<8} {'Controller':<12} "
          f"{'Lead (s)':>14} {'Miss (%)':>14} "
          f"{'Alarm/h':>12} {'Peak (ppm)':>14}")
    print("-" * 100)
    for r in aggregated:
        print(f"{r['scenario']:<8} {r['controller']:<12} "
              f"{r['lead_time_s_mean']:>6.1f}±{r['lead_time_s_std']:<5.1f} "
              f"{r['miss_rate_mean']*100:>6.1f}±{r['miss_rate_std']*100:<5.1f} "
              f"{r['alarms_per_hour_mean']:>6.2f}±{r['alarms_per_hour_std']:<4.2f} "
              f"{r['mean_peak_gas_mean']:>6.0f}±{r['mean_peak_gas_std']:<5.0f}")
    print("=" * 100)


if __name__ == "__main__":
    main()
