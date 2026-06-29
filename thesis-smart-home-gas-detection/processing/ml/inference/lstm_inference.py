"""
LSTM Inference module for gas leak risk prediction.

Loads a Keras `.keras` model and runs inference on a sliding window
of sensor readings per device. Input shape is auto-detected from the
model at load time.

Note: tensorflow and numpy are imported lazily inside LSTMInference.__init__
so that helper functions (_normalise, FEATURES, FEATURE_BOUNDS) can be used
and the module can be imported without TensorFlow being installed.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Tuple

import numpy as np  # numpy 2.x — available on Python 3.14 via pre-built wheel

logger = logging.getLogger(__name__)

# Feature order must match training pipeline
FEATURES = ["gas_ppm", "temperature_c", "humidity_percent"]

# Simple MinMax bounds (from training dataset statistics)
FEATURE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "gas_ppm":           (0.0, 2000.0),
    "temperature_c":     (0.0, 60.0),
    "humidity_percent":  (0.0, 100.0),
}

ALERT_THRESHOLD = float(os.getenv("LSTM_ALERT_THRESHOLD", "0.7"))
WARNING_THRESHOLD = float(os.getenv("LSTM_WARNING_THRESHOLD", "0.4"))


def _normalise(value: float, feat: str) -> float:
    lo, hi = FEATURE_BOUNDS[feat]
    return float(np.clip((value - lo) / (hi - lo + 1e-8), 0.0, 1.0))


@contextmanager
def _compat_dense_from_config(tf):
    """Temporarily drop unsupported Dense config keys during model loading."""
    dense_cls = tf.keras.layers.Dense
    original_from_config = dense_cls.from_config

    def _patched_from_config(cls, config):
        config = dict(config)
        config.pop("quantization_config", None)
        valid_keys = {
            "name", "trainable", "dtype", "units", "activation",
            "use_bias", "kernel_initializer", "bias_initializer",
            "kernel_regularizer", "bias_regularizer",
            "activity_regularizer", "kernel_constraint", "bias_constraint",
        }
        config = {k: v for k, v in config.items() if k in valid_keys}
        return original_from_config(config)

    dense_cls.from_config = classmethod(_patched_from_config)
    try:
        yield
    finally:
        dense_cls.from_config = original_from_config


class LSTMInference:
    """Thread-safe LSTM inference wrapper.

    Usage::
        infer = LSTMInference(model_path)
        risk  = infer.predict(device_id, gas_ppm=350, temperature_c=28, humidity_percent=60)
    """

    def __init__(self, model_path: str | None = None) -> None:
        if model_path is None:
            model_path = os.getenv(
                "LSTM_MODEL_PATH",
                "/app/ml/lstm/gas_forecaster.keras",
            )
        path = Path(model_path)
        # Check path BEFORE importing TF so stub tests work without TF installed
        if not path.exists():
            raise FileNotFoundError(
                f"LSTM model not found: {model_path}\n"
                "Set LSTM_MODEL_PATH or place the file at the default location."
            )

        # Lazy TF import — only runs when a real model file is present
        import tensorflow as tf     # noqa: PLC0415

        logger.info("Loading LSTM model from %s", path)
        _custom_objects = {
            "Orthogonal":  tf.keras.initializers.Orthogonal,
            "orthogonal":  tf.keras.initializers.Orthogonal,
            "GlorotUniform": tf.keras.initializers.GlorotUniform,
            "Zeros":       tf.keras.initializers.Zeros,
            "Ones":        tf.keras.initializers.Ones,
        }

        # Keras 3.x can pass extra config keys to Dense when loading older .keras files.
        # Patch Dense.from_config only for the duration of model loading.
        with _compat_dense_from_config(tf):
            self.model = tf.keras.models.load_model(str(path), custom_objects=_custom_objects)

        # Auto-detect shape from model input spec
        input_shape = self.model.input_shape  # (None, seq_len, n_features)
        self.seq_len: int = int(input_shape[1])
        self.n_features: int = int(input_shape[2])
        logger.info(
            "LSTM model loaded — seq_len=%d, n_features=%d", self.seq_len, self.n_features
        )

        # Per-device sliding window:  device_id -> deque of [n_features] normalised rows
        self._buffers: Dict[str, Deque[List[float]]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(
        self,
        device_id: str,
        gas_ppm: float,
        temperature_c: float,
        humidity_percent: float,
    ) -> float:
        """Return risk score in [0.0, 1.0] for the given device reading.

        Maintains an internal sliding window per device; returns 0.0 until
        the buffer is full (``seq_len`` readings have been observed).
        """
        normalised_row = [
            _normalise(gas_ppm, "gas_ppm"),
            _normalise(temperature_c, "temperature_c"),
            _normalise(humidity_percent, "humidity_percent"),
        ]
        # Truncate / pad to match model's n_features
        normalised_row = (normalised_row + [0.0] * self.n_features)[: self.n_features]

        buf = self._buffers.setdefault(
            device_id, deque(maxlen=self.seq_len)
        )
        buf.append(normalised_row)

        if len(buf) < self.seq_len:
            # Not enough history yet — return proportional placeholder
            return round(gas_ppm / 2000.0, 4)

        x = np.array(list(buf), dtype=np.float32).reshape(1, self.seq_len, self.n_features)
        y = self.model.predict(x, verbose=0)
        return float(round(float(y[0][0]), 4))

    def risk_label(self, score: float) -> str:
        if score >= ALERT_THRESHOLD:
            return "ALERT"
        if score >= WARNING_THRESHOLD:
            return "WARNING"
        return "NORMAL"
