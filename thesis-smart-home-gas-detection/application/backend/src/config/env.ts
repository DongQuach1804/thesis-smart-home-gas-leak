/**
 * Centralised typed environment configuration.
 * All values are read once at startup. Defaults make local dev work without a .env.
 */

function optional(key: string, fallback: string): string {
  return process.env[key] ?? fallback;
}

function bool(key: string, fallback: boolean): boolean {
  const v = process.env[key];
  if (v === undefined) return fallback;
  return /^(1|true|yes|on)$/i.test(v.trim());
}

export const env = {
  nodeEnv: optional("NODE_ENV", "development"),
  apiPort: Number(optional("API_PORT", "3000")),

  influxUrl:    optional("INFLUXDB_URL",        "http://localhost:8086"),
  influxToken:  optional("INFLUXDB_TOKEN",      "thesis-super-token"),
  influxOrg:    optional("INFLUXDB_ORG",        "thesis-org"),
  influxBucket: optional("INFLUXDB_BUCKET_GAS", "gas_sensor_data"),

  kafkaBroker:     optional("KAFKA_BROKER",        "localhost:9092"),
  kafkaAlertTopic: optional("KAFKA_TOPIC_ALERT",   "gas.alert.events"),
  kafkaRawTopic:   optional("KAFKA_TOPIC_RAW_GAS", "gas.raw.sensor"),

  postgresHost:     optional("POSTGRES_HOST",     "localhost"),
  postgresPort:     Number(optional("POSTGRES_PORT", "5432")),
  postgresDb:       optional("POSTGRES_DB",       "gas_metadata"),
  postgresUser:     optional("POSTGRES_USER",     "gas_admin"),
  postgresPassword: optional("POSTGRES_PASSWORD", "gas_admin_123"),

  // Demo fallback — synthesise plausible data when Influx is empty/unreachable
  demoFallback: bool("DEMO_FALLBACK", true),

  // Thresholds (ppm) for risk labelling
  gasPpmWarning: Number(optional("GAS_PPM_WARNING", "400")),
  gasPpmAlert:   Number(optional("GAS_PPM_ALERT",   "700")),
} as const;
