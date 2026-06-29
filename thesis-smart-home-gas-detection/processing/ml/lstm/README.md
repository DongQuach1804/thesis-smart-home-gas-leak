# LSTM Models

Pre-trained Keras LSTM model for gas leak risk forecasting.

## Model File

- **Filename:** `gas_forecaster.keras`
- **Format:** Keras native (`.keras`) — compatible with TensorFlow ≥ 2.12 / Keras 3+
- **Trained on**: simulator-generated gas traces with a 60-sample input window and 300-second forecast horizon
- **Validation note**: Kaggle environmental sensor data is used as an additional public-data check. UCI Gas Sensor Array is a reference dataset for gas time-series characteristics, not the training source of the current deployed forecaster.

## Model Input / Output

| Property | Value |
|---|---|
| Input shape | `(batch, SEQ_LEN, N_FEATURES)` — auto-detected at load time |
| Output | Single sigmoid neuron → `predicted_risk_5min` in `[0.0, 1.0]` |

## Risk Score Thresholds

| Score | Meaning |
|---|---|
| < 0.4 | NORMAL |
| 0.4 – 0.7 | WARNING |
| > 0.7 | ALERT — publishes to `gas.alert.events` Kafka topic |

## Environment Variable

```
LSTM_MODEL_PATH=/app/ml/lstm/gas_forecaster.keras
```
