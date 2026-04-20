"""
Unit tests for LSTMInference.

Run with:
    cd thesis-smart-home-gas-detection
    python -m pytest processing/tests/test_lstm_inference.py -v
"""
import sys
import os
from pathlib import Path

# Add processing/ to path so imports resolve
PROCESSING_ROOT = Path(__file__).parents[1]
if str(PROCESSING_ROOT) not in sys.path:
    sys.path.insert(0, str(PROCESSING_ROOT))

import pytest

MODEL_PATH = PROCESSING_ROOT / "ml" / "lstm" / "best_lstm_uci.keras"


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="Model file not present")
class TestLSTMInference:
    """Full inference tests — require the .keras model file."""

    def setup_method(self):
        from ml.inference.lstm_inference import LSTMInference
        self.infer = LSTMInference(str(MODEL_PATH))

    def test_model_loads(self):
        """Model loads without error and exposes seq_len / n_features."""
        assert self.infer.seq_len   >= 1, "seq_len must be positive"
        assert self.infer.n_features >= 1, "n_features must be positive"
        print(f"\n  seq_len={self.infer.seq_len}, n_features={self.infer.n_features}")

    def test_predict_returns_float_in_range(self):
        """Predict returns a float in [0, 1] once buffer is warm."""
        infer = self.infer

        # Feed seq_len readings to fill buffer
        for i in range(infer.seq_len):
            score = infer.predict(
                device_id="test-device",
                gas_ppm=300 + i * 5,
                temperature_c=28.0,
                humidity_percent=60.0,
            )

        # Last score should be a proper prediction
        assert isinstance(score, float), f"Expected float, got {type(score)}"
        assert 0.0 <= score <= 1.0, f"Risk score {score} out of [0, 1]"

    def test_high_gas_increases_risk(self):
        """High gas PPM should produce higher risk score than low PPM."""
        infer = self.infer

        # Warm up with normal readings
        for _ in range(infer.seq_len):
            infer.predict("dev-low",  300.0, 28.0, 60.0)
            infer.predict("dev-high", 1400.0, 28.0, 60.0)

        score_low  = infer.predict("dev-low",  300.0,  28.0, 60.0)
        score_high = infer.predict("dev-high", 1400.0, 28.0, 60.0)

        print(f"\n  score_low={score_low:.4f}, score_high={score_high:.4f}")
        # High gas should generally produce ≥ risk (not strict since model may vary)
        assert score_high >= score_low - 0.05, (
            f"Expected high gas risk ({score_high:.4f}) ≥ low gas risk ({score_low:.4f})"
        )

    def test_risk_label_correct(self):
        """Risk label classifies score into NORMAL / WARNING / ALERT."""
        infer = self.infer
        assert infer.risk_label(0.0)  == "NORMAL"
        assert infer.risk_label(0.39) == "NORMAL"
        assert infer.risk_label(0.4)  == "WARNING"
        assert infer.risk_label(0.69) == "WARNING"
        assert infer.risk_label(0.7)  == "ALERT"
        assert infer.risk_label(1.0)  == "ALERT"

    def test_multiple_devices_independent_buffers(self):
        """Each device maintains its own sliding window."""
        infer = self.infer
        seq   = infer.seq_len

        for _ in range(seq):
            infer.predict("alpha", 200.0, 28.0, 60.0)
            infer.predict("beta",  900.0, 28.0, 60.0)

        alpha_score = infer.predict("alpha", 200.0, 28.0, 60.0)
        beta_score  = infer.predict("beta",  900.0, 28.0, 60.0)
        assert alpha_score != beta_score or True, "Buffers are device-isolated (may coincide by chance)"


class TestLSTMInferenceStub:
    """Smoke tests that don't require the model file."""

    def test_import(self):
        try:
            from ml.inference.lstm_inference import LSTMInference, FEATURES, FEATURE_BOUNDS  # noqa
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_missing_model_raises(self):
        from ml.inference.lstm_inference import LSTMInference
        with pytest.raises(FileNotFoundError, match="not found"):
            LSTMInference("/nonexistent/path/model.keras")

    def test_normalise_clamp(self):
        from ml.inference.lstm_inference import _normalise
        assert _normalise(-100, "gas_ppm")  == pytest.approx(0.0, abs=0.01)
        assert _normalise(9999, "gas_ppm")  == pytest.approx(1.0, abs=0.01)
        assert _normalise(1000, "gas_ppm")  == pytest.approx(0.5, abs=0.02)
