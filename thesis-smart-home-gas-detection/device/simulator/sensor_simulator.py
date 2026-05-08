"""
Realistic gas-sensor simulator with a leak state machine.

States
------
NORMAL          : background gas 50-150 ppm, small noise
LEAK_SLOW       : slow valve leak, gas grows ~5 ppm/s with noise
LEAK_FAST       : pipe burst, gas grows exponentially
VENTILATING     : after action (fan / valve close), gas decays back to NORMAL

The simulator publishes the standard fields used by the model (gas_ppm,
temperature_c, humidity_percent, event_ts), plus two SIDE-CHANNEL labels
for evaluation only:

    leak_state            : ground-truth state ("NORMAL", "LEAK_SLOW", ...)
    seconds_to_critical   : seconds until gas would exceed 1000 ppm
                            (-1 if not on a leak trajectory)

These ground-truth fields are tagged with a leading underscore so consumers
that don't need them ignore them, and the ML pipeline never feeds them into
the model. The benchmark script joins on event_ts to evaluate lead time.

Environment variables
---------------------
SIM_PUBLISH_HZ        : publish rate in Hz (default 1.0)
SIM_LEAK_PROB_PER_MIN : probability of a leak starting in any given minute
                        while NORMAL (default 0.10)
SIM_SEED              : random seed for reproducible benchmarks (optional)
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_SENSOR", "sensors/gas")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32-lab-01")

PUBLISH_HZ = float(os.getenv("SIM_PUBLISH_HZ", "1.0"))
LEAK_PROB_PER_MIN = float(os.getenv("SIM_LEAK_PROB_PER_MIN", "0.05"))
CRITICAL_PPM = float(os.getenv("SIM_CRITICAL_PPM", "1000.0"))

_seed = os.getenv("SIM_SEED")
if _seed:
    random.seed(int(_seed))


class State(str, Enum):
    NORMAL = "NORMAL"
    LEAK_SLOW = "LEAK_SLOW"
    LEAK_FAST = "LEAK_FAST"
    VENTILATING = "VENTILATING"


@dataclass
class World:
    """Physical state of the room."""
    gas: float = 60.0
    temp: float = 28.0
    hum: float = 60.0
    state: State = State.NORMAL
    state_age_s: float = 0.0


def _step_normal(w: World, dt: float) -> None:
    target = 60.0
    w.gas += (target - w.gas) * 0.1 * dt + random.gauss(0, 3) * dt
    w.gas = max(20.0, min(w.gas, 200.0))
    w.temp += random.gauss(0, 0.05)
    w.hum += random.gauss(0, 0.1)


def _step_leak_slow(w: World, dt: float) -> None:
    # ~5 ppm/s linear growth + noise; saturates around 1500
    rate = 5.0
    w.gas += rate * dt + random.gauss(0, 2) * dt
    w.gas = min(w.gas, 1500.0)
    # Slight humidity rise from gas displacement
    w.hum += 0.02 * dt


def _step_leak_fast(w: World, dt: float) -> None:
    # Exponential growth: gas[t+dt] = gas * exp(k*dt) + base_rate*dt
    k = 0.04
    w.gas = w.gas * math.exp(k * dt) + 8.0 * dt + random.gauss(0, 3) * dt
    w.gas = min(w.gas, 2000.0)
    w.hum += 0.05 * dt


def _step_ventilating(w: World, dt: float) -> None:
    # Exponential decay back to background
    w.gas = max(60.0, w.gas * math.exp(-0.03 * dt) - 0.5 * dt)
    w.temp += random.gauss(0, 0.05)
    w.hum -= 0.05 * dt


STEP_FN = {
    State.NORMAL: _step_normal,
    State.LEAK_SLOW: _step_leak_slow,
    State.LEAK_FAST: _step_leak_fast,
    State.VENTILATING: _step_ventilating,
}


def _maybe_transition(w: World, dt: float) -> None:
    """Stochastic state transitions (no agent acting on the world)."""
    p_per_step = LEAK_PROB_PER_MIN / 60.0 * dt

    if w.state == State.NORMAL:
        if random.random() < p_per_step:
            # 70% slow leaks, 30% fast leaks
            w.state = State.LEAK_SLOW if random.random() < 0.7 else State.LEAK_FAST
            w.state_age_s = 0.0
            return

    if w.state in (State.LEAK_SLOW, State.LEAK_FAST):
        # Self-resolve faster than before so RL training sees balanced episodes
        # (without action a leak ends in ~3-5 minutes, e.g. tank empties).
        if w.state_age_s > 180 and random.random() < 0.005:
            w.state = State.VENTILATING
            w.state_age_s = 0.0
            return

    if w.state == State.VENTILATING:
        if w.gas < 100 and w.state_age_s > 30:
            w.state = State.NORMAL
            w.state_age_s = 0.0


def _seconds_to_critical(w: World) -> int:
    """Estimate seconds until gas crosses CRITICAL_PPM, given current dynamics."""
    if w.gas >= CRITICAL_PPM:
        return 0
    if w.state == State.LEAK_SLOW:
        return max(0, int((CRITICAL_PPM - w.gas) / 5.0))
    if w.state == State.LEAK_FAST:
        # Solve gas * exp(k*t) = CRITICAL → t = ln(C/gas)/k
        if w.gas <= 0:
            return -1
        return max(0, int(math.log(CRITICAL_PPM / w.gas) / 0.04))
    return -1


def build_payload(w: World) -> dict:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "device_id": DEVICE_ID,
        "gas_ppm": round(w.gas, 2),
        "temperature_c": round(w.temp, 2),
        "humidity_percent": round(w.hum, 2),
        "event_ts": now_ms,
        # Side-channel ground truth (only used by benchmark, NOT by the model)
        "_leak_state": w.state.value,
        "_seconds_to_critical": _seconds_to_critical(w),
    }


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    world = World()
    dt = 1.0 / PUBLISH_HZ
    print(f"[simulator] publishing to {MQTT_TOPIC} @ {PUBLISH_HZ} Hz, "
          f"leak prob = {LEAK_PROB_PER_MIN}/min, critical = {CRITICAL_PPM} ppm")

    while True:
        STEP_FN[world.state](world, dt)
        _maybe_transition(world, dt)
        world.state_age_s += dt

        payload = build_payload(world)
        client.publish(MQTT_TOPIC, json.dumps(payload))
        print(f"  state={world.state.value:<11} gas={payload['gas_ppm']:7.1f} "
              f"ttc={payload['_seconds_to_critical']:>4}s")
        time.sleep(dt)


if __name__ == "__main__":
    main()
