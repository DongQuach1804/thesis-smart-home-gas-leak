import json
import logging
import os
import time

from dotenv import load_dotenv
from kafka import KafkaProducer
import paho.mqtt.client as mqtt

# Setup logging with DEBUG level for detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s — %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_SENSOR", "sensors/gas")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "30"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "mqtt-kafka-bridge")
MQTT_RECONNECT_MIN = int(os.getenv("MQTT_RECONNECT_MIN", "1"))
MQTT_RECONNECT_MAX = int(os.getenv("MQTT_RECONNECT_MAX", "30"))
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC_RAW_GAS", "gas.raw.sensor")

logger.info(f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}, topic={MQTT_TOPIC}")
logger.info(f"Kafka broker={KAFKA_BROKER}, topic={KAFKA_TOPIC}")
logger.info("MQTT keepalive=%s client_id=%s", MQTT_KEEPALIVE, MQTT_CLIENT_ID)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)
logger.info("Kafka producer initialized")


def on_connect(client, _userdata, _flags, rc):
    if rc == 0:
        logger.info(f"MQTT connected successfully, subscribing to {MQTT_TOPIC}")
        result = client.subscribe(MQTT_TOPIC)
        logger.info(f"Subscribe result: {result}")
    else:
        logger.error(f"MQTT connect failed with code {rc}")


def on_disconnect(client, _userdata, rc):
    if rc != 0:
        logger.warning(f"MQTT disconnected unexpectedly with code {rc}")
    else:
        logger.info(f"MQTT disconnected cleanly (rc={rc})")


def on_subscribe(client, _userdata, mid, granted_qos):
    logger.info(f"Subscribe acknowledged: mid={mid}, qos={granted_qos}")


def on_message(_client, _userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        payload["bridge_timestamp"] = int(time.time() * 1000)
        logger.info(f"[BRIDGE] Received from {msg.topic}: device={payload.get('device_id')}, gas={payload.get('gas_ppm')}")
        producer.send(KAFKA_TOPIC, payload)
        producer.flush()
        logger.info(f"[BRIDGE] Sent to Kafka {KAFKA_TOPIC}: device={payload.get('device_id')}")
    except Exception as exc:
        logger.error(f"[BRIDGE] Error processing message: {exc}", exc_info=True)


if __name__ == "__main__":
    client_id = MQTT_CLIENT_ID or None
    clean_session = False if client_id else True
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION1,
        client_id=client_id,
        clean_session=clean_session,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    
    # Disable automatic reconnection handling - we'll handle it manually
    # This prevents aggressive reconnect cycles that might interfere with subscriptions
    client.reconnect_delay_set(min_delay=MQTT_RECONNECT_MIN, max_delay=MQTT_RECONNECT_MAX)
    client.max_queued_messages_set(0)  # Unlimited queue
    
    try:
        logger.info("Attempting initial MQTT connection...")
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=MQTT_KEEPALIVE)
    except Exception as e:
        logger.error(f"Failed to connect: {e}", exc_info=True)
        exit(1)
    
    try:
        # Use standard loop_forever() for robust operation
        client.loop_forever()
    except KeyboardInterrupt:
        logger.info("Bridge interrupted, disconnecting...")
        client.disconnect()
        client.loop_stop()
