# End-to-End Data Flow

1. Device Layer
- ESP32 or simulator publishes gas sensor payload (ppm, temperature, humidity, timestamp) to MQTT topic `sensors/gas`.

2. Communication Layer
- Mosquitto receives MQTT packets.
- Bridge service subscribes MQTT and republishes JSON messages to Kafka topic `gas.raw.sensor`.

3. Processing Layer
- Spark Structured Streaming consumes Kafka topic in near real-time.
- Stream job performs parsing, validation, and feature extraction.
- LSTM model predicts leak risk score from temporal sequence.
- RL PPO agent selects mitigation action (normal/ventilate/alarm/shutoff).
- Processed measurements and predictions are written to InfluxDB.
- Alert events and audit logs can be written to PostgreSQL.

4. Application Layer
- Node.js TypeScript API queries InfluxDB/PostgreSQL and exposes REST endpoints.
- Frontend (Express + EJS/static) consumes API and renders dashboard.
- Grafana visualizes time-series trends, risk score, and action history.
