/**
 * InfluxDB service — Flux queries for gas sensor readings and LSTM predictions.
 *
 * Uses @influxdata/influxdb-client (the official v2 client).
 * All Flux queries return strongly-typed domain objects.
 */
import { InfluxDB, QueryApi } from "@influxdata/influxdb-client";
import { env } from "../config/env";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface GasReading {
  deviceId:         string;
  gasPpm:           number;
  temperatureC:     number;
  humidityPercent:  number;
  lstmRiskScore:    number;
  riskLabel:        string;
  ts:               string;   // ISO-8601
}

// ─── Service ──────────────────────────────────────────────────────────────────

class InfluxService {
  private readonly queryApi: QueryApi;

  constructor() {
    const client = new InfluxDB({ url: env.influxUrl, token: env.influxToken });
    this.queryApi = client.getQueryApi(env.influxOrg);
  }

  /**
   * Latest sensor reading for a device (or the most recent device if omitted).
   */
  async getLatestReading(deviceId = ""): Promise<GasReading | null> {
    const deviceFilter = deviceId
      ? `|> filter(fn: (r) => r.device_id == "${deviceId}")`
      : "";

    const flux = `
      from(bucket: "${env.influxBucket}")
        |> range(start: -15m)
        |> filter(fn: (r) => r._measurement == "gas_reading")
        ${deviceFilter}
        |> pivot(rowKey: ["_time","device_id","risk_label"], columnKey: ["_field"], valueColumn: "_value")
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: 1)
    `;

    return new Promise((resolve, reject) => {
      const rows: GasReading[] = [];
      this.queryApi.queryRows(flux, {
        next: (row, meta) => {
          const o = meta.toObject(row);
          rows.push({
            deviceId:        String(o["device_id"]   ?? ""),
            gasPpm:          Number(o["gas_ppm"]      ?? 0),
            temperatureC:    Number(o["temperature_c"] ?? 0),
            humidityPercent: Number(o["humidity_percent"] ?? 0),
            lstmRiskScore:   Number(o["lstm_risk_score"]  ?? 0),
            riskLabel:       String(o["risk_label"]   ?? "NORMAL"),
            ts:              String(o["_time"]         ?? new Date().toISOString()),
          });
        },
        error: reject,
        complete: () => resolve(rows[0] ?? null),
      });
    });
  }

  /**
   * Historical readings for charting — last `minutes` minutes, sampled
   * every `sampleEvery` seconds.
   */
  async getHistoricalReadings(
    deviceId = "",
    minutes = 30,
    sampleEvery = 10
  ): Promise<GasReading[]> {
    const deviceFilter = deviceId
      ? `|> filter(fn: (r) => r.device_id == "${deviceId}")`
      : "";

    const flux = `
      from(bucket: "${env.influxBucket}")
        |> range(start: -${minutes}m)
        |> filter(fn: (r) => r._measurement == "gas_reading")
        ${deviceFilter}
        |> pivot(rowKey: ["_time","device_id","risk_label"], columnKey: ["_field"], valueColumn: "_value")
        |> aggregateWindow(every: ${sampleEvery}s, fn: last, createEmpty: false)
        |> sort(columns: ["_time"], desc: false)
    `;

    return new Promise((resolve, reject) => {
      const rows: GasReading[] = [];
      this.queryApi.queryRows(flux, {
        next: (row, meta) => {
          const o = meta.toObject(row);
          rows.push({
            deviceId:        String(o["device_id"]    ?? ""),
            gasPpm:          Number(o["gas_ppm"]       ?? 0),
            temperatureC:    Number(o["temperature_c"]  ?? 0),
            humidityPercent: Number(o["humidity_percent"] ?? 0),
            lstmRiskScore:   Number(o["lstm_risk_score"]  ?? 0),
            riskLabel:       String(o["risk_label"]    ?? "NORMAL"),
            ts:              String(o["_time"]          ?? ""),
          });
        },
        error: reject,
        complete: () => resolve(rows),
      });
    });
  }
}

// Export singleton
export const influxService = new InfluxService();
