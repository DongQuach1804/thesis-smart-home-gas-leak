CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'viewer',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS system_logs (
  id BIGSERIAL PRIMARY KEY,
  service_name VARCHAR(120) NOT NULL,
  level VARCHAR(20) NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_events (
  id BIGSERIAL PRIMARY KEY,
  device_id VARCHAR(120) NOT NULL,
  gas_ppm DOUBLE PRECISION NOT NULL,
  predicted_risk_5min DOUBLE PRECISION NOT NULL,
  risk_label VARCHAR(40) NOT NULL,
  event_ts BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alert_events_device_ts ON alert_events (device_id, event_ts DESC);

CREATE TABLE IF NOT EXISTS action_events (
  id BIGSERIAL PRIMARY KEY,
  device_id VARCHAR(120) NOT NULL,
  action VARCHAR(40) NOT NULL,         -- NO_OP | ALERT_USER | FAN_ON | CLOSE_VALVE
  action_id INT NOT NULL,
  trigger_p5 DOUBLE PRECISION NOT NULL,
  gas_ppm DOUBLE PRECISION NOT NULL,
  event_ts BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_action_events_device_ts ON action_events (device_id, event_ts DESC);
