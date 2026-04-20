"""
Spark Structured Streaming processor — gas leak detection pipeline.

Data flow:
  Kafka (gas.raw.sensor)
    → parse JSON
    → enrich with LSTM risk score (sliding window per device)
    → write to InfluxDB  (gas_reading measurement + lstm_risk_score field)
    → if risk_score > threshold → publish alert to Kafka (gas.alert.events)

NOTE: pyspark, influxdb_client, and kafka are imported lazily inside
functions so that unit tests can mock them via conftest without needing
the full stack installed.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("stream_processor")


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# Lazy heavy imports  (pyspark / kafka / influxdb_client)
# These are imported at call time so tests can patch them without needing
# the actual packages installed.
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
# Singleton LSTM model (lazy-loaded once per worker process)
# ---------------------------------------------------------------------------
_lstm_inference = None


def _get_lstm():
    """Lazy-load LSTMInference in the executor process."""
    global _lstm_inference
    if _lstm_inference is None:
        # Add processing package root to path so imports work inside Docker
        pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        )))
        if pkg_root not in sys.path:
            sys.path.insert(0, pkg_root)
        try:
            from ml.inference.lstm_inference import LSTMInference  # noqa: PLC0415
            model_path = _env("LSTM_MODEL_PATH", "/app/ml/lstm/best_lstm_uci.keras")
            _lstm_inference = LSTMInference(model_path)
            logger.info("LSTM model loaded successfully from %s", model_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load LSTM model: %s", exc)
            _lstm_inference = None
    return _lstm_inference


# ---------------------------------------------------------------------------
# Kafka alert producer (singleton per process)
# ---------------------------------------------------------------------------
_alert_producer = None


def _get_alert_producer():
    global _alert_producer
    if _alert_producer is None:
        broker = _env("KAFKA_BROKER", "kafka:9092")
        try:
            KafkaProducer = _import_kafka_producer()
            _alert_producer = KafkaProducer(
                bootstrap_servers=broker,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=3,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Alert producer not available: %s", exc)
    return _alert_producer


# ---------------------------------------------------------------------------
# Spark session
# ---------------------------------------------------------------------------

def get_spark():
    SparkSession, *_ = _import_pyspark()
    return (
        SparkSession.builder
        .master("local[*]")          # embedded Spark — no external master needed
        .appName("GasLeakStreamProcessor")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.driver.host", "localhost")
        .config("spark.driver.bindAddress", "0.0.0.0")
        .getOrCreate()
    )


# ---------------------------------------------------------------------------
# foreachBatch handler  (the main testable unit)
# ---------------------------------------------------------------------------

def write_batch(df, batch_id: int) -> None:
    if df.rdd.isEmpty():
        return

    # Import heavy deps lazily so tests can mock them
    InfluxDBClient, Point, WritePrecision, SYNCHRONOUS = _import_influx()

    influx_url    = _env("INFLUXDB_URL",       "http://influxdb:8086")
    influx_token  = _env("INFLUXDB_TOKEN",      "thesis-super-token")
    influx_org    = _env("INFLUXDB_ORG",        "thesis-org")
    influx_bucket = _env("INFLUXDB_BUCKET_GAS", "gas_sensor_data")
    alert_topic   = _env("KAFKA_TOPIC_ALERT",   "gas.alert.events")

    lstm           = _get_lstm()
    alert_producer = _get_alert_producer()

    rows   = df.collect()
    points = []

    for row in rows:
        device_id        = row.device_id or "unknown"
        gas_ppm          = float(row.gas_ppm)
        temperature_c    = float(row.temperature_c)
        humidity_percent = float(row.humidity_percent)
        event_ts         = int(row.event_ts)

        # ── LSTM inference ──────────────────────────────────────────────────
        risk_score = 0.0
        risk_label = "NORMAL"
        if lstm is not None:
            try:
                risk_score = lstm.predict(device_id, gas_ppm, temperature_c, humidity_percent)
                risk_label = lstm.risk_label(risk_score)
            except Exception as exc:  # noqa: BLE001
                logger.warning("LSTM predict error for %s: %s", device_id, exc)

        # ── InfluxDB point ──────────────────────────────────────────────────
        point = (
            Point("gas_reading")
            .tag("device_id",  device_id)
            .tag("risk_label", risk_label)
            .field("gas_ppm",          gas_ppm)
            .field("temperature_c",    temperature_c)
            .field("humidity_percent", humidity_percent)
            .field("lstm_risk_score",  risk_score)
            .time(event_ts, WritePrecision.MS)
        )
        points.append(point)

        logger.info(
            "batch=%d device=%s gas=%.1f risk=%.4f [%s]",
            batch_id, device_id, gas_ppm, risk_score, risk_label,
        )

        # ── Alert publishing ────────────────────────────────────────────────
        if risk_label in ("ALERT", "WARNING") and alert_producer is not None:
            alert_payload = {
                "device_id":    device_id,
                "gas_ppm":      gas_ppm,
                "risk_score":   risk_score,
                "risk_label":   risk_label,
                "event_ts":     event_ts,
                "published_at": int(time.time() * 1000),
            }
            try:
                alert_producer.send(alert_topic, alert_payload)
                alert_producer.flush()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Alert publish failed: %s", exc)

    # ── Write batch to InfluxDB ─────────────────────────────────────────────
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
