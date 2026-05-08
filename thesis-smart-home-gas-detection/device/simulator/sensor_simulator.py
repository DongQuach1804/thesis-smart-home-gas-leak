import json
import logging
import os
import random
import time
from datetime import datetime, timezone

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


def generate_payload() -> dict:
    gas = random.uniform(100, 800)
    if random.random() < 0.05:
        gas = random.uniform(900, 1500)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return {
        "device_id": DEVICE_ID,
        "gas_ppm": round(gas, 2),
        "temperature_c": round(random.uniform(25, 35), 2),
        "humidity_percent": round(random.uniform(45, 80), 2),
        "event_ts": now_ms,
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


if __name__ == "__main__":
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
    logger.info("Starting to publish sensor data...")
    
    try:
        counter = 0
        while True:
            if not client.is_connected():
                try:
                    client.reconnect()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"Reconnect failed: {exc}")
                    time.sleep(1)
                    continue

            payload = generate_payload()
            result = client.publish(MQTT_TOPIC, json.dumps(payload))
            if result.rc == 0:
                logger.info(f"Published (#{counter}): gas={payload['gas_ppm']} ppm, temp={payload['temperature_c']}°C")
            else:
                logger.warning(f"Publish failed: {result.rc}")
            counter += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.loop_stop()
        client.disconnect()
