"""
Gas-leak FORECASTING module (the scientific core of the thesis).

Unlike the legacy ``LSTMInference`` which classifies "is current state
abnormal", this module answers a forward-looking question:

    P( max gas_ppm over the next H seconds > CRITICAL )

So the dashboard can warn BEFORE the gas reaches dangerous levels.

The model is a small Keras sequence model trained by
``processing/ml/lstm/train_forecaster.py``. If the trained file is missing,
this module falls back to a deterministic *trend extrapolator* so the
pipeline still produces meaningful predictions for development.
"""
from __future__ import annotations

import logging
import math
import os
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

FEATURES = ("gas_ppm", "temperature_c", "humidity_percent")
FEATURE_BOUNDS = {
    "gas_ppm": (0.0, 2000.0),
    "temperature_c": (0.0, 60.0),
    "humidity_percent": (0.0, 100.0),
}

HORIZON_SECONDS = int(os.getenv("FORECAST_HORIZON_SECONDS", "300"))   # 5 min
CRITICAL_PPM = float(os.getenv("FORECAST_CRITICAL_PPM", "1000.0"))
SEQ_LEN = int(os.getenv("FORECAST_SEQ_LEN", "60"))                     # 60 s window


def _norm(v: float, feat: str) -> float:
    lo, hi = FEATURE_BOUNDS[feat]
    return float(np.clip((v - lo) / (hi - lo + 1e-8), 0.0, 1.0))


class _TrendFallback:
    """Deterministic baseline that estimates P(gas > CRITICAL within H seconds)
    by linear / exponential extrapolation on the last ``SEQ_LEN`` samples.

    Used when the trained Keras forecaster is unavailable so the pipeline
    still produces meaningful predicted-risk values for the dashboard during
    development.
    """

    def predict_proba(self, window_raw: np.ndarray) -> float:
        gas = window_raw[:, 0]
        if len(gas) < 5:
            return 0.0

        current = float(gas[-1])
        if current >= CRITICAL_PPM:
            return 1.0

        # Linear slope (ppm / sample) using last N samples
        n = min(len(gas), 30)
        x = np.arange(n, dtype=np.float32)
        slope, intercept = np.polyfit(x, gas[-n:], 1)
        linear_pred = current + slope * HORIZON_SECONDS

        # Exponential fit if growth is positive
        exp_pred = current
        if slope > 0.5 and current > 30:
            tail = gas[-min(len(gas), 15):]
            ratios = tail[1:] / np.maximum(tail[:-1], 1e-3)
            k = float(np.log(np.clip(np.mean(ratios), 1e-3, 5.0)))
            if k > 0:
                exp_pred = current * math.exp(k * HORIZON_SECONDS)

        predicted = max(linear_pred, exp_pred)
        # Smoothly map predicted value to probability using a soft margin
        # around CRITICAL_PPM so values just below 1000 still indicate risk.
        margin = 200.0
        prob = 1.0 / (1.0 + math.exp(-(predicted - CRITICAL_PPM) / margin))
        return float(round(prob, 4))


class GasForecaster:
    """Wraps either a trained Keras model or the trend fallback.

    Usage::

        f = GasForecaster()
        p = f.predict("esp32-lab-01", gas_ppm=420, temperature_c=29, humidity_percent=62)
        # p in [0, 1] — probability gas exceeds CRITICAL within HORIZON seconds
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.seq_len = SEQ_LEN
        self.horizon_s = HORIZON_SECONDS
        self.critical_ppm = CRITICAL_PPM
        self._model = None
        self._fallback = _TrendFallback()
        self._buffers: Dict[str, Deque[list[float]]] = {}
        self._raw_buffers: Dict[str, Deque[list[float]]] = {}

        path = Path(model_path or os.getenv(
            "FORECAST_MODEL_PATH",
            "/app/ml/lstm/gas_forecaster.keras",
        ))
        if path.exists():
            try:
                import tensorflow as tf  # local import to keep startup light
                self._model = tf.keras.models.load_model(str(path))
                input_shape = self._model.input_shape
                self.seq_len = int(input_shape[1])
                logger.info(
                    "Forecaster loaded from %s — seq_len=%d", path, self.seq_len
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load forecaster (%s); using trend fallback", exc)
                self._model = None
        else:
            logger.warning(
                "Forecaster model not found at %s — using trend extrapolation fallback",
                path,
            )

    def predict(
        self,
        device_id: str,
        gas_ppm: float,
        temperature_c: float,
        humidity_percent: float,
    ) -> float:
        norm_row = [
            _norm(gas_ppm, "gas_ppm"),
            _norm(temperature_c, "temperature_c"),
            _norm(humidity_percent, "humidity_percent"),
        ]
        raw_row = [gas_ppm, temperature_c, humidity_percent]

        nbuf = self._buffers.setdefault(device_id, deque(maxlen=self.seq_len))
        rbuf = self._raw_buffers.setdefault(device_id, deque(maxlen=self.seq_len))
        nbuf.append(norm_row)
        rbuf.append(raw_row)

        if self._model is not None and len(nbuf) == self.seq_len:
            x = np.array(list(nbuf), dtype=np.float32).reshape(1, self.seq_len, 3)
            y = self._model.predict(x, verbose=0)
            return float(round(float(y[0][0]), 4))

        # Fallback: trend extrapolation — works even with partial buffer
        return self._fallback.predict_proba(np.array(list(rbuf), dtype=np.float32))

    @staticmethod
    def label(prob: float) -> str:
        if prob >= 0.7:
            return "ALERT"
        if prob >= 0.4:
            return "WARNING"
        return "NORMAL"
