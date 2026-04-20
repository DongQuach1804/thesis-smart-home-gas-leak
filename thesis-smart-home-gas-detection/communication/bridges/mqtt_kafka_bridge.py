import json
import os
import time

from dotenv import load_dotenv
from kafka import KafkaProducer
import paho.mqtt.client as mqtt

load_dotenv()

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_SENSOR", "sensors/gas")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_RAW_GAS", "gas.raw.sensor")

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"MQTT connect failed with code {rc}")


def on_message(_client, _userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        payload["bridge_timestamp"] = int(time.time() * 1000)
        producer.send(KAFKA_TOPIC, payload)
        producer.flush()
    except Exception as exc:
        print(f"Bridge error: {exc}")


if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()
