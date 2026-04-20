"""
Unit tests for stream_processor.write_batch (foreachBatch handler).

Since `spark-streaming` contains a hyphen it cannot be a Python package.
conftest.py stubs pyspark/kafka/influxdb_client before any import happens.
We patch stream_processor's lazy-import helpers and InfluxDBClient to keep
tests fully isolated from the infrastructure.

Run with (from project root):
    python -m pytest processing/tests/test_stream_processor.py -v --tb=short
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

# ── Path setup already done by conftest.py ────────────────────────────────────
# PROCESSING_ROOT and JOBS_PATH are inserted in sys.path by conftest.


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_row(
    device_id="dev-01",
    gas_ppm=350.0,
    temp=28.0,
    hum=60.0,
    ts=1_700_000_000_000,
):
    """Create a mock Spark Row object."""
    r = MagicMock()
    r.device_id        = device_id
    r.gas_ppm          = gas_ppm
    r.temperature_c    = temp
    r.humidity_percent = hum
    r.event_ts         = ts
    return r


def _make_df(*rows):
    """Create a mock Spark DataFrame."""
    df = MagicMock()
    df.rdd.isEmpty.return_value = (len(rows) == 0)
    df.collect.return_value     = list(rows)
    return df


def _mock_influx_chain(mock_import_influx):
    """
    Helper: configure _import_influx() to return mock InfluxDB objects.
    Returns (mock_client, mock_writer) already wired together.
    """
    mock_InfluxDBClient = MagicMock()
    mock_Point          = MagicMock(side_effect=lambda m: MagicMock())
    mock_WritePrecision = MagicMock()
    mock_SYNCHRONOUS    = object()

    mock_import_influx.return_value = (
        mock_InfluxDBClient, mock_Point, mock_WritePrecision, mock_SYNCHRONOUS
    )

    mock_writer = MagicMock()
    mock_ctx    = MagicMock()
    mock_ctx.write_api.return_value = mock_writer
    mock_InfluxDBClient.return_value.__enter__ = MagicMock(return_value=mock_ctx)
    mock_InfluxDBClient.return_value.__exit__  = MagicMock(return_value=False)

    return mock_InfluxDBClient, mock_writer


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestWriteBatch:
    """Tests for write_batch — the core foreachBatch handler."""

    # ── empty df ─────────────────────────────────────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_empty_df_is_skipped(self, mock_prod, mock_lstm, mock_influx):
        """Empty DataFrames must not trigger any writes or LSTM calls."""
        from stream_processor import write_batch
        write_batch(_make_df(), batch_id=0)

        mock_influx.assert_not_called()
        mock_lstm.assert_not_called()
        mock_prod.assert_not_called()

    # ── lstm called per row ───────────────────────────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_lstm_called_for_each_row(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """LSTM predict is called exactly once per row."""
        lstm = MagicMock()
        lstm.predict.return_value    = 0.15
        lstm.risk_label.return_value = "NORMAL"
        mock_lstm_fn.return_value    = lstm
        mock_prod_fn.return_value    = None

        _mock_influx_chain(mock_influx_fn)

        df = _make_df(
            _make_row("dev-01", gas_ppm=300.0),
            _make_row("dev-02", gas_ppm=450.0),
        )

        from stream_processor import write_batch
        write_batch(df, batch_id=1)

        assert lstm.predict.call_count == 2

    # ── alert published for ALERT ─────────────────────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_alert_published_for_high_risk(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """Alert producer.send() called once for ALERT risk label."""
        lstm = MagicMock()
        lstm.predict.return_value    = 0.92
        lstm.risk_label.return_value = "ALERT"
        mock_lstm_fn.return_value    = lstm

        alert_producer = MagicMock()
        mock_prod_fn.return_value = alert_producer

        _mock_influx_chain(mock_influx_fn)

        df = _make_df(_make_row("dev-01", gas_ppm=1200.0))

        from stream_processor import write_batch
        write_batch(df, batch_id=2)

        alert_producer.send.assert_called_once()
        payload = alert_producer.send.call_args[0][1]
        assert payload["risk_label"] == "ALERT"
        assert payload["device_id"]  == "dev-01"
        assert payload["gas_ppm"]    == pytest.approx(1200.0)
        assert payload["risk_score"] == pytest.approx(0.92)

    # ── no alert for NORMAL ───────────────────────────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_no_alert_for_normal_risk(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """Alert producer must NOT be called for NORMAL readings."""
        lstm = MagicMock()
        lstm.predict.return_value    = 0.12
        lstm.risk_label.return_value = "NORMAL"
        mock_lstm_fn.return_value    = lstm

        alert_producer = MagicMock()
        mock_prod_fn.return_value = alert_producer

        _mock_influx_chain(mock_influx_fn)

        df = _make_df(_make_row("dev-01", gas_ppm=200.0))

        from stream_processor import write_batch
        write_batch(df, batch_id=3)

        alert_producer.send.assert_not_called()

    # ── alert published for WARNING ───────────────────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_alert_published_for_warning(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """Alert producer.send() called for WARNING risk label too."""
        lstm = MagicMock()
        lstm.predict.return_value    = 0.55
        lstm.risk_label.return_value = "WARNING"
        mock_lstm_fn.return_value    = lstm

        alert_producer = MagicMock()
        mock_prod_fn.return_value = alert_producer

        _mock_influx_chain(mock_influx_fn)

        df = _make_df(_make_row("dev-01", gas_ppm=600.0))

        from stream_processor import write_batch
        write_batch(df, batch_id=4)

        alert_producer.send.assert_called_once()
        assert alert_producer.send.call_args[0][1]["risk_label"] == "WARNING"

    # ── graceful degradation when LSTM unavailable ────────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_lstm_none_still_writes_raw(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """If LSTM fails to load, write_batch must still write raw sensor data."""
        mock_lstm_fn.return_value = None
        mock_prod_fn.return_value = None

        _, mock_writer = _mock_influx_chain(mock_influx_fn)

        df = _make_df(_make_row("dev-01", gas_ppm=350.0))

        from stream_processor import write_batch
        write_batch(df, batch_id=5)   # must not raise

        mock_writer.write.assert_called_once()

    # ── influx write called with correct point count ──────────────────────────

    @patch("stream_processor._import_influx")
    @patch("stream_processor._get_lstm")
    @patch("stream_processor._get_alert_producer")
    def test_influx_write_called_with_all_points(self, mock_prod_fn, mock_lstm_fn, mock_influx_fn):
        """InfluxDB write is called once with all rows in the batch."""
        lstm = MagicMock()
        lstm.predict.return_value    = 0.1
        lstm.risk_label.return_value = "NORMAL"
        mock_lstm_fn.return_value    = lstm
        mock_prod_fn.return_value    = None

        _, mock_writer = _mock_influx_chain(mock_influx_fn)

        df = _make_df(
            _make_row("dev-01"),
            _make_row("dev-02"),
            _make_row("dev-03"),
        )

        from stream_processor import write_batch
        write_batch(df, batch_id=6)

        mock_writer.write.assert_called_once()
        # The 'record' kwarg should contain all 3 points
        write_kwargs = mock_writer.write.call_args[1]
        assert len(write_kwargs["record"]) == 3
