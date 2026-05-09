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
    if _lstm_inference is None:
        _ensure_path()
        try:
            from ml.inference.lstm_inference import LSTMInference
            path = _env("LSTM_MODEL_PATH", "/app/ml/lstm/best_lstm_uci.keras")
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
    spark_driver_host = os.getenv("SPARK_DRIVER_HOST")
    spark_driver_bind_address = _env("SPARK_DRIVER_BIND_ADDRESS", "0.0.0.0")

    builder = (
        SparkSession.builder
        .master("local[*]")
        .appName("GasLeakStreamProcessor")
        .config("spark.sql.shuffle.partitions", "2")
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
    if df.rdd.isEmpty():
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

    legacy_lstm = _get_lstm()
    forecaster  = _get_forecaster()
    rl_agent    = _get_rl_agent()
    alert_prod  = _get_alert_producer()
    action_prod = _get_action_producer()

    rows = df.collect()
    points = []

    for row in rows:
        device_id        = row.device_id or "unknown"
        gas_ppm          = float(row.gas_ppm)
        temperature_c    = float(row.temperature_c)
        humidity_percent = float(row.humidity_percent)
        event_ts         = int(row.event_ts)

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
            .time(event_ts, WritePrecision.MS)
        )
        points.append(point)

        logger.info(
            "batch=%d device=%s gas=%6.1f legacy=%.3f p5min=%.3f [%s] action=%s",
            batch_id, device_id, gas_ppm, legacy_score, p5, p5_label, action_name,
        )

        # ── Publish predictive alert ────────────────────────────────────
        if p5_label != "NORMAL" and alert_prod is not None:
            try:
                alert_prod.send(alert_topic, {
                    "device_id":            device_id,
                    "gas_ppm":              gas_ppm,
                    "predicted_risk_5min":  p5,
                    "risk_label":           p5_label,
                    "horizon_seconds":      forecaster.horizon_s,
                    "event_ts":             event_ts,
                    "published_at":         int(time.time() * 1000),
                })
                alert_prod.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Alert publish failed: %s", exc)

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
                action_prod.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Action publish failed: %s", exc)

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

    logger.info("Connecting to Kafka broker=%s topic=%s", kafka_broker, kafka_topic)

    raw_df = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_broker)
        .option("subscribe", kafka_topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .option("kafka.request.timeout.ms", "120000")
        .option("kafka.session.timeout.ms", "120000")
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
        .option("checkpointLocation", "/tmp/spark-checkpoints/gas")
        .trigger(processingTime="5 seconds")
        .start()
    )

    logger.info("Stream processor started — awaiting termination")
    query.awaitTermination()


if __name__ == "__main__":
    main()
