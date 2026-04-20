import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_SENSOR", "sensors/gas")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32-lab-01")


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


if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    while True:
        payload = generate_payload()
        client.publish(MQTT_TOPIC, json.dumps(payload))
        print(payload)
        time.sleep(1)
