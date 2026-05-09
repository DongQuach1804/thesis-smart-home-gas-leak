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
import logging
import math
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import paho.mqtt.client as mqtt

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
)
logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_SENSOR", "sensors/gas")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32-lab-01")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "30"))

logger.info(f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}, topic={MQTT_TOPIC}")

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


def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        logger.info("Simulator connected to MQTT successfully")
    else:
        logger.error(f"MQTT connect failed with code {rc}")


def on_publish(client, _userdata, mid):
    logger.debug(f"Message {mid} published")


def on_disconnect(client, _userdata, rc):
    if rc != 0:
        logger.warning(f"MQTT disconnected unexpectedly with code {rc}")
    else:
        logger.info("MQTT disconnected cleanly")


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    try:
        client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
    except Exception as e:
        logger.error(f"Failed to connect to MQTT: {e}", exc_info=True)
        exit(1)

    client.loop_start()
    world = World()
    dt = 1.0 / PUBLISH_HZ
    logger.info(
        f"Publishing to {MQTT_TOPIC} @ {PUBLISH_HZ} Hz, "
        f"leak prob = {LEAK_PROB_PER_MIN}/min, critical = {CRITICAL_PPM} ppm"
    )

    counter = 0
    try:
        while True:
            if not client.is_connected():
                try:
                    client.reconnect()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Reconnect failed: {exc}")
                    time.sleep(1)
                    continue

            STEP_FN[world.state](world, dt)
            _maybe_transition(world, dt)
            world.state_age_s += dt

            payload = build_payload(world)
            result = client.publish(MQTT_TOPIC, json.dumps(payload))
            if result.rc == 0:
                logger.info(
                    f"#{counter} state={world.state.value:<11} "
                    f"gas={payload['gas_ppm']:7.1f} ppm "
                    f"ttc={payload['_seconds_to_critical']:>4}s"
                )
            else:
                logger.warning(f"Publish failed: {result.rc}")
            counter += 1
            time.sleep(dt)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
