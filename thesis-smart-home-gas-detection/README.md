# Smart Home Gas Leak Detection Thesis Platform

A clean-slate, 4-layer IoT architecture for a graduation thesis:

- Device Layer
- Communication Layer
- Processing Layer
- Application Layer

This project demonstrates integrated IoT streaming + Big Data + Deep Learning + Reinforcement Learning:

`ESP32/Sensor Simulator -> MQTT -> Kafka -> Spark Structured Streaming + LSTM/RL Inference -> InfluxDB/PostgreSQL -> Node.js API -> Web Dashboard`

## Core Stack

- Python 3.11 (processing and ML)
- Node.js 22 LTS + TypeScript + Express (backend)
- Express + EJS/static assets (frontend)
- InfluxDB 2.7, PostgreSQL 16
- Mosquitto MQTT, Apache Kafka, Apache Spark (PySpark Structured Streaming)
- TensorFlow/Keras LSTM (.h5), Stable-Baselines3 PPO (.zip)
- Docker + Docker Compose (dev and prod)
- Grafana

## Start

1. Copy `.env.example` to `.env` and adjust values.
2. Development mode (hot-reload):
   - `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
3. Production-like mode:
   - `docker compose up --build -d`

## Documentation

- `docs/PROJECT_STRUCTURE.md`
- `docs/TECH_STACK_VERSIONS.md`
- `docs/DATA_FLOW.md`
