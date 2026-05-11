/**
 * Centralised typed environment configuration.
 * All values are read once at startup; process exits if a required var is missing.
 */

function required(key: string): string {
  const v = process.env[key];
  if (!v) throw new Error(`Missing required env var: ${key}`);
  return v;
}

function optional(key: string, fallback: string): string {
  return process.env[key] ?? fallback;
}

export const env = {
  nodeEnv: optional("NODE_ENV", "development"),
  apiPort: Number(optional("API_PORT", "3000")),

  influxUrl:    optional("INFLUXDB_URL",        "http://localhost:8086"),
  influxToken:  optional("INFLUXDB_TOKEN",       "thesis-super-token"),
  influxOrg:    optional("INFLUXDB_ORG",         "thesis-org"),
  influxBucket: optional("INFLUXDB_BUCKET_GAS",  "gas_sensor_data"),
  dashboardLatestMaxAgeSec: Number(optional("DASHBOARD_LATEST_MAX_AGE_SEC", "60")),

  kafkaBroker:      optional("KAFKA_BROKER",           "localhost:9092"),
  kafkaAlertTopic:  optional("KAFKA_TOPIC_ALERT",      "gas.alert.events"),
  kafkaActionTopic: optional("KAFKA_TOPIC_ACTION",     "gas.action.events"),
  kafkaRawTopic:    optional("KAFKA_TOPIC_RAW_GAS",    "gas.raw.sensor"),
  kafkaAlertGroupId:  optional("KAFKA_ALERT_GROUP_ID",  "gas-backend-alerts-v2"),
  kafkaActionGroupId: optional("KAFKA_ACTION_GROUP_ID", "gas-backend-actions-v2"),

  postgresHost:     optional("POSTGRES_HOST",     "localhost"),
  postgresPort:     Number(optional("POSTGRES_PORT", "5432")),
  postgresDb:       optional("POSTGRES_DB",       "gas_metadata"),
  postgresUser:     optional("POSTGRES_USER",     "gas_admin"),
  postgresPassword: optional("POSTGRES_PASSWORD", "gas_admin_123"),

  telegramEnabled:      optional("TELEGRAM_ENABLED", "false"),
  telegramBotToken:     optional("TELEGRAM_BOT_TOKEN", ""),
  telegramChatId:       optional("TELEGRAM_CHAT_ID", ""),
  telegramMinRiskScore: Number(optional("TELEGRAM_MIN_RISK_SCORE", "0.7")),
  telegramCooldownSec:  Number(optional("TELEGRAM_COOLDOWN_SEC", "5")),
  telegramRiskLabels:   optional("TELEGRAM_RISK_LABELS", "ALERT,WARNING,CRITICAL"),
  telegramMonitorIntervalSec: Number(optional("TELEGRAM_MONITOR_INTERVAL_SEC", "5")),
  telegramNotifyFromKafka: optional("TELEGRAM_NOTIFY_FROM_KAFKA", "false"),
  alertMaxAgeSec:       Number(optional("ALERT_MAX_AGE_SEC", "120")),
  displayTimeZone:      optional("DISPLAY_TIME_ZONE", "Asia/Ho_Chi_Minh"),
  gasAlertPpm:          Number(optional("GAS_ALERT_PPM", "1000")),
  gasWarningPpm:        Number(optional("GAS_WARNING_PPM", "700")),
} as const;
