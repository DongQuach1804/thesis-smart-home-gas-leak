"""
Spark Structured Streaming pipeline — gas-leak forecasting + RL response.

For every reading the pipeline computes THREE quantities:

  1. ``lstm_risk_score``         legacy anomaly score (current state)
  2. ``predicted_risk_5min``     P(gas > 1000 ppm in next 300 s)  ← forecasting
  3. ``rl_action``               action chosen by the PPO controller
                                 (NO_OP / ALERT_USER / FAN_ON / CLOSE_VALVE)

It then:
  • writes all three to InfluxDB measurement ``gas_reading``,
  • publishes alerts (threshold on ``predicted_risk_5min``) to Kafka, and
  • publishes the chosen action to a separate Kafka topic so downstream
    actuators (relays / smart-home hub) can subscribe.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("stream_processor")


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Lazy heavy imports
# ---------------------------------------------------------------------------

def _import_influx():
    from influxdb_client import InfluxDBClient, Point, WritePrecision  # noqa: PLC0415
    from influxdb_client.client.write_api import SYNCHRONOUS            # noqa: PLC0415
    return InfluxDBClient, Point, WritePrecision, SYNCHRONOUS


def _import_kafka_producer():
    from kafka import KafkaProducer  # noqa: PLC0415
    return KafkaProducer


def _import_pyspark():
    from pyspark.sql import SparkSession                             # noqa: PLC0415
    from pyspark.sql.functions import col, from_json                 # noqa: PLC0415
    from pyspark.sql.types import (                                  # noqa: PLC0415
        DoubleType, LongType, StringType, StructField, StructType,
    )
    return SparkSession, col, from_json, DoubleType, LongType, StringType, StructField, StructType


# ---------------------------------------------------------------------------
# Lazy singletons (per executor process)
# ---------------------------------------------------------------------------

_lstm_inference = None
_forecaster = None
_rl_agent = None
_alert_producer = None
_action_producer = None
_telegram_last_sent_by_key: dict[str, float] = {}


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


class _RuleOnlyAgent:
    """Small local fallback so dev streaming does not import PPO dependencies."""

    def choose(
        self,
        _device_id: str,
        gas_ppm: float,
        _temperature_c: float,
        _humidity_percent: float,
        p_critical_5min: float,
    ):
        if gas_ppm >= 900.0 or (gas_ppm >= 700.0 and p_critical_5min >= 0.7):
            return 3, "CLOSE_VALVE"
        if gas_ppm >= 600.0 or p_critical_5min >= 0.4:
            return 2, "FAN_ON"
        if p_critical_5min >= 0.3:
            return 1, "ALERT_USER"
        return 0, "NO_OP"


def _telegram_enabled() -> bool:
    return _truthy(_env("TELEGRAM_SEND_FROM_PROCESSING", "false"))


def _format_event_time(event_ts: int) -> str:
    try:
        return datetime.fromtimestamp(event_ts / 1000, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return str(event_ts)


def _normalize_epoch_ms(value: int | float | str) -> int:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return int(time.time() * 1000)
    if not parsed or parsed <= 0:
        return int(time.time() * 1000)
    return int(parsed * 1000) if parsed < 1_000_000_000_000 else int(parsed)


def _is_stale_event(event_ts: int, max_age_s: float) -> bool:
    if max_age_s <= 0:
        return False
    return int(time.time() * 1000) - event_ts > max_age_s * 1000


def _alert_source_label(source: str) -> str:
    return {
        "REALTIME_GAS": "Real/simulation gas threshold",
        "LSTM_FORECAST": "LSTM forecast threshold",
    }.get(source, source or "Unknown")


def _current_gas_label(gas_ppm: float, warning_ppm: float, alert_ppm: float) -> str:
    if gas_ppm >= alert_ppm:
        return "ALERT"
    if gas_ppm >= warning_ppm:
        return "WARNING"
    return "NORMAL"


def _build_alert_payload(
    *,
    source: str,
    device_id: str,
    gas_ppm: float,
    p5: float,
    risk_label: str,
    horizon_seconds: int,
    event_ts: int,
    action_id: int,
    action_name: str,
    legacy_score: float,
    legacy_label: str,
    alert_score: float,
) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "alert_source":         source,
        "device_id":            device_id,
        "gas_ppm":              gas_ppm,
        "predicted_risk_5min":  p5,
        "risk_score":           alert_score,
        "risk_label":           risk_label,
        "horizon_seconds":      horizon_seconds,
        "event_ts":             event_ts,
        "alert_time":           _format_event_time(event_ts),
        "published_at":         now_ms,
        "rl_action_id":         action_id,
        "rl_action":            action_name,
        "lstm_risk_score":      legacy_score,
        "lstm_risk_label":      legacy_label,
    }


def _send_telegram_alert(alert: dict) -> None:
    """Best-effort Telegram notification from the alert producer path."""
    if not _telegram_enabled():
        return

    token = _env("TELEGRAM_BOT_TOKEN", "")
    chat_id = _env("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logger.warning("Telegram enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing")
        return

    min_risk = float(_env("TELEGRAM_MIN_RISK_SCORE", "0.7"))
    cooldown_s = max(0.0, float(_env("TELEGRAM_COOLDOWN_SEC", "60")))
    allowed_labels = {
        label.strip().upper()
        for label in _env("TELEGRAM_RISK_LABELS", "ALERT,WARNING,CRITICAL").split(",")
        if label.strip()
    }

    risk = float(alert.get("risk_score", alert.get("predicted_risk_5min", 0.0)) or 0.0)
    label = str(alert.get("risk_label", "")).upper()
    device_id = str(alert.get("device_id", "unknown"))
    source = str(alert.get("alert_source", "LSTM_FORECAST"))

    if risk < min_risk:
        return
    if allowed_labels and label not in allowed_labels:
        return

    now = time.time()
    cooldown_key = f"{device_id}:{source}:{label}"
    last_sent = _telegram_last_sent_by_key.get(cooldown_key, 0.0)
    if now - last_sent < cooldown_s:
        return
    _telegram_last_sent_by_key[cooldown_key] = now

    event_ts = int(alert.get("event_ts", int(now * 1000)) or int(now * 1000))
    p5 = float(alert.get("predicted_risk_5min", 0.0) or 0.0)
    action = str(alert.get("rl_action", "NO_OP"))
    action_id = int(alert.get("rl_action_id", 0) or 0)
    text = "\n".join([
        f"GAS ALERT - {_alert_source_label(source)}",
        f"alert_time: {_format_event_time(event_ts)}",
        f"device: {device_id}",
        f"gas_ppm: {float(alert.get('gas_ppm', 0.0) or 0.0):.1f}",
        f"risk_label: {label}",
        f"risk_score: {risk:.4f}",
        f"lstm_prediction_5min: {p5:.4f}",
        f"rl_action: {action} ({action_id})",
    ])
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310
            if res.status >= 400:
                logger.warning("Telegram send failed: HTTP %s", res.status)
                return
        logger.info("Telegram alert sent for device %s", device_id)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Telegram send error: %s", exc)


def _ensure_path():
    pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    repo_root = os.path.dirname(pkg_root)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def _get_lstm():
    """Legacy anomaly LSTM (kept for backward compatibility)."""
    global _lstm_inference
    if not _truthy(_env("LSTM_LEGACY_ENABLED", "true")):
        return None
    if _lstm_inference is None:
        _ensure_path()
        try:
            from ml.inference.lstm_inference import LSTMInference
            path = _env("LSTM_MODEL_PATH", "/app/ml/lstm/gas_forecaster.keras")
            _lstm_inference = LSTMInference(path)
            logger.info("Legacy LSTM loaded from %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Legacy LSTM unavailable: %s", exc)
            _lstm_inference = None
    return _lstm_inference


def _get_forecaster():
    global _forecaster
    if _forecaster is None:
        _ensure_path()
        from ml.inference.forecaster_inference import GasForecaster
        path = _env("FORECAST_MODEL_PATH", "/app/ml/lstm/gas_forecaster.keras")
        _forecaster = GasForecaster(path)
    return _forecaster


def _get_rl_agent():
    global _rl_agent
    if _rl_agent is None:
        if not _truthy(_env("RL_MODEL_LOAD_ENABLED", "true")):
            logger.info("PPO model loading disabled; using rule-only RL fallback")
            _rl_agent = _RuleOnlyAgent()
            return _rl_agent
        _ensure_path()
        from ml.inference.rl_inference import GasResponseAgent
        path = _env("RL_MODEL_PATH", "/app/ml/rl/ppo_gas_agent.zip")
        _rl_agent = GasResponseAgent(path)
    return _rl_agent


def _producer(topic_env: str):
    broker = _env("KAFKA_BROKER", "kafka:9092")
    KafkaProducer = _import_kafka_producer()
    return KafkaProducer(
        bootstrap_servers=broker,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=3,
    )


def _get_alert_producer():
    global _alert_producer
    if _alert_producer is None:
        try:
            _alert_producer = _producer("KAFKA_TOPIC_ALERT")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alert producer unavailable: %s", exc)
    return _alert_producer


def _get_action_producer():
    global _action_producer
    if _action_producer is None:
        try:
            _action_producer = _producer("KAFKA_TOPIC_ACTION")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Action producer unavailable: %s", exc)
    return _action_producer


# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------

def get_spark():
    SparkSession, *_ = _import_pyspark()
    spark_master = _env("SPARK_MASTER", "local[2]")
    spark_driver_host = os.getenv("SPARK_DRIVER_HOST")
    spark_driver_bind_address = _env("SPARK_DRIVER_BIND_ADDRESS", "0.0.0.0")

    builder = (
        SparkSession.builder
        .master(spark_master)
        .appName("GasLeakStreamProcessor")
        .config("spark.sql.shuffle.partitions", _env("SPARK_SQL_SHUFFLE_PARTITIONS", "1"))
        .config("spark.default.parallelism", _env("SPARK_DEFAULT_PARALLELISM", "2"))
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.driver.bindAddress", spark_driver_bind_address)
    )

    # In containerized local mode, hard-coding localhost can break RPC lookups.
    # Only set spark.driver.host when explicitly provided.
    if spark_driver_host:
        builder = builder.config("spark.driver.host", spark_driver_host)

    return (
        builder
        .getOrCreate()
    )


# ---------------------------------------------------------------------------
# foreachBatch handler
# ---------------------------------------------------------------------------

def write_batch(df, batch_id: int) -> None:
    rows = df.collect()
    if not rows:
        return

    InfluxDBClient, Point, WritePrecision, SYNCHRONOUS = _import_influx()

    influx_url    = _env("INFLUXDB_URL",       "http://influxdb:8086")
    influx_token  = _env("INFLUXDB_TOKEN",      "thesis-super-token")
    influx_org    = _env("INFLUXDB_ORG",        "thesis-org")
    influx_bucket = _env("INFLUXDB_BUCKET_GAS", "gas_sensor_data")
    alert_topic   = _env("KAFKA_TOPIC_ALERT",   "gas.alert.events")
    action_topic  = _env("KAFKA_TOPIC_ACTION",  "gas.action.events")
    forecast_alert_threshold = float(_env("FORECAST_ALERT_THRESHOLD", "0.7"))
    forecast_warn_threshold  = float(_env("FORECAST_WARN_THRESHOLD",  "0.4"))
    raw_max_age_s = float(_env("RAW_SENSOR_MAX_AGE_SEC", "0"))
    use_ingest_time = _truthy(_env("RAW_SENSOR_USE_INGEST_TIME", "false"))
    gas_alert_ppm = float(_env(
        "GAS_ALERT_PPM",
        _env("SIM_CRITICAL_PPM", _env("FORECAST_CRITICAL_PPM", "1000.0")),
    ))
    gas_warning_ppm = float(_env("GAS_WARNING_PPM", str(gas_alert_ppm * 0.7)))

    legacy_lstm = _get_lstm()
    forecaster  = _get_forecaster()
    rl_agent    = _get_rl_agent()
    alert_prod  = _get_alert_producer()
    action_prod = _get_action_producer()

    points = []
    alert_messages_sent = False
    action_messages_sent = False

    batch_ingest_base_ms = int(time.time() * 1000)

    for row_index, row in enumerate(rows):
        device_id        = row.device_id or "unknown"
        gas_ppm          = float(row.gas_ppm)
        temperature_c    = float(row.temperature_c)
        humidity_percent = float(row.humidity_percent)
        source_event_ts  = _normalize_epoch_ms(row.event_ts)
        event_ts         = batch_ingest_base_ms + row_index if use_ingest_time else source_event_ts
        if not use_ingest_time and _is_stale_event(event_ts, raw_max_age_s):
            logger.warning(
                "Skipping stale sensor row: device=%s age_sec=%d gas=%.1f",
                device_id,
                int((int(time.time() * 1000) - event_ts) / 1000),
                gas_ppm,
            )
            continue

        # ── 1. Legacy anomaly LSTM (kept for comparison / dashboards) ───
        legacy_score = 0.0
        legacy_label = "NORMAL"
        if legacy_lstm is not None:
            try:
                legacy_score = legacy_lstm.predict(
                    device_id, gas_ppm, temperature_c, humidity_percent
                )
                legacy_label = legacy_lstm.risk_label(legacy_score)
            except Exception as exc:  # noqa: BLE001
                logger.warning("legacy LSTM error for %s: %s", device_id, exc)

        # ── 2. Forecasting LSTM — P(gas critical in 5 min) ──────────────
        try:
            p5 = forecaster.predict(device_id, gas_ppm, temperature_c, humidity_percent)
        except Exception as exc:  # noqa: BLE001
            logger.warning("forecaster error: %s", exc)
            p5 = 0.0
        p5_label = (
            "ALERT" if p5 >= forecast_alert_threshold
            else "WARNING" if p5 >= forecast_warn_threshold
            else "NORMAL"
        )

        # ── 3. RL controller chooses an action ──────────────────────────
        try:
            action_id, action_name = rl_agent.choose(
                device_id, gas_ppm, temperature_c, humidity_percent, p5,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("RL agent error: %s", exc)
            action_id, action_name = 0, "NO_OP"

        # ── Persist to InfluxDB ─────────────────────────────────────────
        processed_at_ms = int(time.time() * 1000)
        point = (
            Point("gas_reading")
            .tag("device_id",  device_id)
            .tag("risk_label", p5_label)
            .tag("rl_action",  action_name)
            .field("gas_ppm",             gas_ppm)
            .field("temperature_c",       temperature_c)
            .field("humidity_percent",    humidity_percent)
            .field("lstm_risk_score",     legacy_score)
            .field("predicted_risk_5min", p5)
            .field("rl_action_id",        action_id)
            .field("event_ts_ms",         source_event_ts)
            .field("processed_at_ms",     processed_at_ms)
            .field("pipeline_latency_ms", max(0, processed_at_ms - source_event_ts))
            .time(event_ts, WritePrecision.MS)
        )
        points.append(point)

        logger.info(
            "batch=%d device=%s gas=%6.1f legacy=%.3f p5min=%.3f [%s] action=%s",
            batch_id, device_id, gas_ppm, legacy_score, p5, p5_label, action_name,
        )

        # ── Publish real/simulation threshold alert and LSTM forecast alert ──
        current_gas_label = _current_gas_label(gas_ppm, gas_warning_ppm, gas_alert_ppm)
        alert_payloads = []
        if current_gas_label != "NORMAL":
            gas_score = min(max(gas_ppm / gas_alert_ppm, 0.0), 1.0) if gas_alert_ppm > 0 else 1.0
            alert_payloads.append(_build_alert_payload(
                source="REALTIME_GAS",
                device_id=device_id,
                gas_ppm=gas_ppm,
                p5=p5,
                risk_label=current_gas_label,
                horizon_seconds=forecaster.horizon_s,
                event_ts=event_ts,
                action_id=action_id,
                action_name=action_name,
                legacy_score=legacy_score,
                legacy_label=legacy_label,
                alert_score=gas_score,
            ))
        if p5_label != "NORMAL":
            alert_payloads.append(_build_alert_payload(
                source="LSTM_FORECAST",
                device_id=device_id,
                gas_ppm=gas_ppm,
                p5=p5,
                risk_label=p5_label,
                horizon_seconds=forecaster.horizon_s,
                event_ts=event_ts,
                action_id=action_id,
                action_name=action_name,
                legacy_score=legacy_score,
                legacy_label=legacy_label,
                alert_score=p5,
            ))

        for alert_payload in alert_payloads:
            if alert_prod is not None:
                try:
                    alert_prod.send(alert_topic, alert_payload)
                    alert_messages_sent = True
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Alert publish failed: %s", exc)
            _send_telegram_alert(alert_payload)

        # ── Publish RL action so actuators / smart-home hub can react ───
        if action_id != 0 and action_prod is not None:
            try:
                action_prod.send(action_topic, {
                    "device_id":   device_id,
                    "action_id":   action_id,
                    "action":      action_name,
                    "trigger_p5":  p5,
                    "gas_ppm":     gas_ppm,
                    "event_ts":    event_ts,
                })
                action_messages_sent = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("Action publish failed: %s", exc)

    if alert_messages_sent and alert_prod is not None:
        try:
            alert_prod.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alert producer flush failed: %s", exc)

    if action_messages_sent and action_prod is not None:
        try:
            action_prod.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Action producer flush failed: %s", exc)

    if not points:
        logger.info("No fresh sensor points to write (batch %d)", batch_id)
        return

    try:
        with InfluxDBClient(url=influx_url, token=influx_token, org=influx_org) as client:
            writer = client.write_api(write_options=SYNCHRONOUS)
            writer.write(bucket=influx_bucket, org=influx_org, record=points)
        logger.info("Wrote %d points to InfluxDB (batch %d)", len(points), batch_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("InfluxDB write error: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    (
        SparkSession, col, from_json,
        DoubleType, LongType, StringType, StructField, StructType,
    ) = _import_pyspark()

    spark = get_spark()
    spark.sparkContext.setLogLevel("WARN")

    schema = StructType([
        StructField("device_id",        StringType(), True),
        StructField("gas_ppm",          DoubleType(), True),
        StructField("temperature_c",    DoubleType(), True),
        StructField("humidity_percent", DoubleType(), True),
        StructField("event_ts",         LongType(),   True),
    ])

    kafka_broker = _env("KAFKA_BROKER",        "kafka:9092")
    kafka_topic  = _env("KAFKA_TOPIC_RAW_GAS", "gas.raw.sensor")
    max_offsets_per_trigger = _env("SPARK_MAX_OFFSETS_PER_TRIGGER", "20")
    checkpoint_location = _env("SPARK_CHECKPOINT_LOCATION", "/tmp/spark-checkpoints/gas")
    kafka_timeout_ms = _env("SPARK_KAFKA_TIMEOUT_MS", "300000")
    kafka_offset_retries = _env("SPARK_KAFKA_OFFSET_RETRIES", "10")
    kafka_offset_retry_interval_ms = _env("SPARK_KAFKA_OFFSET_RETRY_INTERVAL_MS", "10000")

    logger.info("Connecting to Kafka broker=%s topic=%s", kafka_broker, kafka_topic)

    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_broker)
        .option("subscribe", kafka_topic)
        .option("startingOffsets", "latest")
        .option("maxOffsetsPerTrigger", max_offsets_per_trigger)
        .option("failOnDataLoss", "false")
        .option("kafka.request.timeout.ms", kafka_timeout_ms)
        .option("kafka.default.api.timeout.ms", kafka_timeout_ms)
        .option("kafka.session.timeout.ms", "60000")
        .option("kafkaConsumer.pollTimeoutMs", kafka_timeout_ms)
        .option("fetchOffset.numRetries", kafka_offset_retries)
        .option("fetchOffset.retryIntervalMs", kafka_offset_retry_interval_ms)
        .option("kafka.metadata.max.age.ms", "30000")
        .load()
    )

    parsed_df = (
        raw_df
        .selectExpr("CAST(value AS STRING) AS payload")
        .select(from_json(col("payload"), schema).alias("d"))
        .select("d.*")
        .filter(col("gas_ppm").isNotNull())
    )

    query = (
        parsed_df.writeStream
        .outputMode("append")
        .foreachBatch(write_batch)
        .option("checkpointLocation", checkpoint_location)
        .trigger(processingTime="5 seconds")
        .start()
    )

    logger.info("Stream processor started — awaiting termination")
    query.awaitTermination()


if __name__ == "__main__":
    main()
