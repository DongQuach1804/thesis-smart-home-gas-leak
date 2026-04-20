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

  kafkaBroker:      optional("KAFKA_BROKER",           "localhost:9092"),
  kafkaAlertTopic:  optional("KAFKA_TOPIC_ALERT",      "gas.alert.events"),
  kafkaRawTopic:    optional("KAFKA_TOPIC_RAW_GAS",    "gas.raw.sensor"),

  postgresHost:     optional("POSTGRES_HOST",     "localhost"),
  postgresPort:     Number(optional("POSTGRES_PORT", "5432")),
  postgresDb:       optional("POSTGRES_DB",       "gas_metadata"),
  postgresUser:     optional("POSTGRES_USER",     "gas_admin"),
  postgresPassword: optional("POSTGRES_PASSWORD", "gas_admin_123"),
} as const;
