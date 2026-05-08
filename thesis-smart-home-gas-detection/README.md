# Smart Home Gas-Leak Predictive Response Platform

A 4-layer IoT platform that does **predictive** gas-leak warning and
**autonomous response**, not just real-time gas measurement.

## Scientific contribution

Most commercial gas detectors (and most prior thesis projects) are
**threshold alarms**: they fire only after gas has already reached a
dangerous concentration — the same moment a person can smell it. By then,
the warning is just a confirmation.

This project replaces that pattern with a two-stage AI system:

1. **Forecasting LSTM** — answers
   `P(gas_ppm > 1000 within next 300 s)` so the platform warns *before*
   the gas crosses critical, when there is still time to act.
2. **PPO Reinforcement-Learning controller** — chooses, every second,
   between `NO_OP / ALERT_USER / FAN_ON / CLOSE_VALVE`. Rewards favour
   stopping leaks at low cost and penalise both missed leaks and false
   alarms. The learned policy is the *scientific contribution*: it
   demonstrates that an RL agent trained on the simulator's physics
   outperforms static thresholds on lead time, miss rate, and false-alarm
   rate.

The **benchmark script** [`processing/scripts/benchmark.py`](processing/scripts/benchmark.py)
runs three controllers (`THRESHOLD`, `FORECASTER`, `RL`) on the same
deterministic simulation seed and reports `lead_time_s`, `miss_rate`,
`false_alarm_per_min`, and `mean_peak_gas` — these are the numbers to
quote in the thesis evaluation chapter.

## Architecture

```
ESP32 / sensor simulator
   │  MQTT  (sensors/gas)
   ▼
Mosquitto ──► mqtt-kafka-bridge ──► Kafka (gas.raw.sensor)
                                       │
                                       ▼
                           Spark Structured Streaming
                          ┌──────────────────────────┐
                          │ 1. Forecasting LSTM      │  → predicted_risk_5min
                          │ 2. PPO controller        │  → rl_action
                          └──────────────────────────┘
                                       │
                ┌──────────────────────┼─────────────────────┐
                ▼                      ▼                     ▼
         InfluxDB (time-series)  Kafka gas.alert.events  Kafka gas.action.events
                │                      │                     │
                ▼                      ▼                     ▼
         Backend API ── SSE ─► Dashboard           Postgres (alert + action history)
```

## Repository layout (key files)

| Path | Purpose |
|---|---|
| `device/simulator/sensor_simulator.py` | Realistic leak state-machine (NORMAL → LEAK_SLOW / LEAK_FAST → VENTILATING) with ground-truth labels |
| `processing/ml/inference/forecaster_inference.py` | Forecaster wrapper (Keras model + trend-extrapolation fallback) |
| `processing/ml/lstm/train_forecaster.py` | Trains the forecasting LSTM on simulator-generated data |
| `processing/ml/rl/gas_env.py` | Gymnasium environment over the simulator physics |
| `processing/ml/rl/train_rl.py` | PPO training script |
| `processing/ml/inference/rl_inference.py` | Policy wrapper (PPO + rule-based fallback) |
| `processing/spark-streaming/jobs/stream_processor.py` | Pipeline that runs forecaster + RL per reading |
| `processing/scripts/benchmark.py` | Controller comparison for the thesis evaluation |
| `application/backend/src/services/postgres.service.ts` | Alert + action persistence |
| `application/frontend/views/dashboard.ejs` | Dashboard with predicted-risk gauge and live RL action |

## Running everything

### 1. Train the models (one-time)

```bash
pip install -r processing/requirements-processing.txt

# Forecasting LSTM (writes processing/ml/lstm/gas_forecaster.keras)
python processing/ml/lstm/train_forecaster.py --hours 4 --epochs 15

# RL controller       (writes processing/ml/rl/ppo_gas_agent.zip)
python processing/ml/rl/train_rl.py --steps 200000
```

If you skip these steps the pipeline still runs — the forecaster falls
back to **trend extrapolation** and the RL controller to a **rule-based**
policy. Both fallbacks are deterministic and good enough for development.

### 2. Run the evaluation benchmark

```bash
python processing/scripts/benchmark.py --hours 6 --seed 42
```

Produces the comparison table for the thesis report.

### 3. Bring up the platform

```bash
cp .env.example .env
docker compose up --build
# Dashboard: http://localhost:8080
# Grafana:   http://localhost:3001  (admin / admin123456)
```

## What changed vs. the original code

* **Simulator** — was `random.uniform(100, 800)`; now a stateful physical
  model that simulates real leak dynamics and emits ground-truth labels.
* **LSTM** — was an "is current state abnormal" classifier; now a
  forward-looking probability `P(critical within 5 minutes)` (the
  forecasting model).
* **RL** — previously declared but unused; now a Gymnasium env, PPO
  training script, and inference wrapper that participates in the live
  pipeline and publishes actions to Kafka / Postgres.
* **Pipeline** — `stream_processor.py` runs forecaster + RL alongside the
  legacy LSTM and writes all three to InfluxDB per reading.
* **Backend** — new `postgres.service.ts` persists alerts and actions;
  new `/api/dashboard/alerts` and `/api/dashboard/actions` endpoints.
* **Dashboard** — gauge now shows the **predicted** 5-min risk; a new
  "Auto Action (RL)" card displays the chosen controller action live.

## Documentation

- `docs/PROJECT_STRUCTURE.md`
- `docs/TECH_STACK_VERSIONS.md`
- `docs/DATA_FLOW.md`
