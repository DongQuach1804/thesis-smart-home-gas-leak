import json
import logging
import os
import queue
import signal
import threading
import time

from dotenv import load_dotenv
from kafka import KafkaProducer
import paho.mqtt.client as mqtt

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except Exception:  # pragma: no cover - optional fast path
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None

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
KAFKA_QUEUE_MAXSIZE = int(os.getenv("KAFKA_QUEUE_MAXSIZE", "1000"))
KAFKA_FLUSH_INTERVAL_SEC = float(os.getenv("KAFKA_FLUSH_INTERVAL_SEC", "1.0"))
RAW_INFLUX_WRITE_ENABLED = os.getenv("SIM_RAW_INFLUX_WRITE_ENABLED", "false").lower() in {
    "1", "true", "yes", "on",
}
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "thesis-super-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "thesis-org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET_GAS", "gas_sensor_data")
GAS_ALERT_PPM = float(os.getenv("GAS_ALERT_PPM", os.getenv("SIM_CRITICAL_PPM", "1000.0")))
GAS_WARNING_PPM = float(os.getenv("GAS_WARNING_PPM", str(GAS_ALERT_PPM * 0.7)))

logger.info(f"Connecting to MQTT {MQTT_HOST}:{MQTT_PORT}, topic={MQTT_TOPIC}")
logger.info(f"Kafka broker={KAFKA_BROKER}, topic={KAFKA_TOPIC}")
logger.info("MQTT keepalive=%s client_id=%s", MQTT_KEEPALIVE, MQTT_CLIENT_ID)
logger.info("Raw Influx fast path enabled=%s bucket=%s", RAW_INFLUX_WRITE_ENABLED, INFLUXDB_BUCKET)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    linger_ms=50,
    retries=5,
    max_block_ms=10_000,
)
logger.info("Kafka producer initialized")

message_queue: queue.Queue[dict] = queue.Queue(maxsize=KAFKA_QUEUE_MAXSIZE)
stop_event = threading.Event()
_influx_client = None
_influx_writer = None


def _get_influx_writer():
    global _influx_client, _influx_writer
    if not RAW_INFLUX_WRITE_ENABLED:
        return None
    if InfluxDBClient is None or Point is None:
        logger.warning("[BRIDGE] influxdb-client unavailable; raw Influx write disabled")
        return None
    if _influx_writer is None:
        _influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        _influx_writer = _influx_client.write_api(write_options=SYNCHRONOUS)
        logger.info("[BRIDGE] Raw Influx writer initialized: %s/%s", INFLUXDB_URL, INFLUXDB_BUCKET)
    return _influx_writer


def _write_raw_influx(payload: dict) -> None:
    writer = _get_influx_writer()
    if writer is None:
        return

    ts = int(payload.get("bridge_timestamp") or time.time() * 1000)
    device_id = str(payload.get("device_id") or "unknown")
    gas_ppm = float(payload.get("gas_ppm") or 0.0)
    if gas_ppm >= GAS_ALERT_PPM:
        risk_label, action_name, action_id = "ALERT", "CLOSE_VALVE", 3
    elif gas_ppm >= GAS_WARNING_PPM:
        risk_label, action_name, action_id = "WARNING", "FAN_ON", 2
    else:
        risk_label, action_name, action_id = "NORMAL", "NO_OP", 0

    point = (
        Point("gas_raw_reading")
        .tag("device_id", device_id)
        .tag("risk_label", risk_label)
        .tag("rl_action", action_name)
        .field("gas_ppm", gas_ppm)
        .field("temperature_c", float(payload.get("temperature_c") or 0.0))
        .field("humidity_percent", float(payload.get("humidity_percent") or 0.0))
        .field("lstm_risk_score", 0.0)
        .field("predicted_risk_5min", min(max(gas_ppm / GAS_ALERT_PPM, 0.0), 1.0))
        .field("rl_action_id", action_id)
        .time(ts, WritePrecision.MS)
    )
    writer.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)


def _on_kafka_send_success(record_metadata):
    logger.debug(
        "[BRIDGE] Kafka ack topic=%s partition=%s offset=%s",
        record_metadata.topic,
        record_metadata.partition,
        record_metadata.offset,
    )


def _on_kafka_send_error(exc):
    logger.error("[BRIDGE] Kafka send failed: %s", exc, exc_info=True)


def kafka_worker():
    """Send MQTT payloads to Kafka without blocking the MQTT network loop."""
    last_flush = time.monotonic()

    while not stop_event.is_set() or not message_queue.empty():
        try:
            payload = message_queue.get(timeout=0.2)
        except queue.Empty:
            payload = None

        if payload is not None:
            try:
                producer.send(KAFKA_TOPIC, payload).add_callback(
                    _on_kafka_send_success,
                ).add_errback(_on_kafka_send_error)
                logger.info(
                    "[BRIDGE] Queued to Kafka %s: device=%s",
                    KAFKA_TOPIC,
                    payload.get("device_id"),
                )
            except Exception as exc:
                logger.error("[BRIDGE] Error queueing Kafka message: %s", exc, exc_info=True)
            try:
                _write_raw_influx(payload)
            except Exception as exc:
                logger.warning("[BRIDGE] Raw Influx write failed: %s", exc)
            finally:
                message_queue.task_done()

        now = time.monotonic()
        if now - last_flush >= KAFKA_FLUSH_INTERVAL_SEC:
            try:
                producer.flush(timeout=5)
            except Exception as exc:
                logger.error("[BRIDGE] Kafka flush failed: %s", exc, exc_info=True)
            last_flush = now

    try:
        producer.flush(timeout=10)
    finally:
        producer.close(timeout=10)
        if _influx_client is not None:
            _influx_client.close()


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
        logger.info(
            "[BRIDGE] Received from %s: device=%s, gas=%s",
            msg.topic,
            payload.get("device_id"),
            payload.get("gas_ppm"),
        )
        try:
            message_queue.put_nowait(payload)
        except queue.Full:
            logger.error(
                "[BRIDGE] Kafka queue full (%s); dropping message device=%s",
                KAFKA_QUEUE_MAXSIZE,
                payload.get("device_id"),
            )
    except Exception as exc:
        logger.error(f"[BRIDGE] Error processing message: {exc}", exc_info=True)


if __name__ == "__main__":
    worker = threading.Thread(target=kafka_worker, name="kafka-worker", daemon=True)
    worker.start()

    def _stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    client_id = MQTT_CLIENT_ID or None
    clean_session = True
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
    finally:
        stop_event.set()
        client.disconnect()
        worker.join(timeout=15)
