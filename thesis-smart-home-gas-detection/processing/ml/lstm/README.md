# LSTM Models

Pre-trained Keras LSTM model for gas leak risk prediction.

## Model File

- **Filename:** `best_lstm_uci.keras`
- **Format:** Keras native (`.keras`) — compatible with TensorFlow ≥ 2.12 / Keras 3+
- **Trained on:** UCI HAR / gas sensor dataset

## Model Input / Output

| Property | Value |
|---|---|
| Input shape | `(batch, SEQ_LEN, N_FEATURES)` — auto-detected at load time |
| Output | Single sigmoid neuron → `risk_score` in `[0.0, 1.0]` |

## Risk Score Thresholds

| Score | Meaning |
|---|---|
| < 0.4 | NORMAL |
| 0.4 – 0.7 | WARNING |
| > 0.7 | ALERT — publishes to `gas.alert.events` Kafka topic |

## Environment Variable

```
LSTM_MODEL_PATH=/app/ml/lstm/best_lstm_uci.keras
```
