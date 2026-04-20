"""
conftest.py — Pytest configuration for the processing test suite.

Mocks out heavy dependencies (pyspark, kafka, influxdb_client) at import
time so tests can run without installing the full Spark / Kafka stack.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

# ── Path setup ────────────────────────────────────────────────────────────────
PROCESSING_ROOT = Path(__file__).parent.parent
JOBS_PATH       = PROCESSING_ROOT / "spark-streaming" / "jobs"

for p in [str(PROCESSING_ROOT), str(JOBS_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# ── Stub heavy modules before any test imports them ───────────────────────────

def _stub(name: str) -> MagicMock:
    m = MagicMock()
    sys.modules[name] = m
    return m


# PySpark — not needed for unit tests
_stub("pyspark")
_stub("pyspark.sql")
_stub("pyspark.sql.functions")
_stub("pyspark.sql.types")

# Kafka Python — we mock the producer in tests; stub so import doesn't fail
_stub("kafka")
_stub("kafka.KafkaProducer")

# InfluxDB client — stubbed; tests mock InfluxDBClient directly
_stub("influxdb_client")
_stub("influxdb_client.client")
_stub("influxdb_client.client.write_api")

# Fix: make influxdb_client.Point and WritePrecision importable as real names
import influxdb_client as _ic  # noqa: E402
_ic.Point         = MagicMock
_ic.WritePrecision = MagicMock()

# Fix: SYNCHRONOUS must be an object (used as a kwarg value)
_ic.client.write_api.SYNCHRONOUS = object()
