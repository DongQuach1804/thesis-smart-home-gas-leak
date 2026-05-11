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
  deviceId:           string;
  gasPpm:             number;
  temperatureC:       number;
  humidityPercent:    number;
  lstmRiskScore:      number;       // legacy anomaly score
  predictedRisk5Min:  number;       // P(critical in next 5 min) — forecasting
  riskLabel:          string;
  rlAction:           string;       // NO_OP | ALERT_USER | FAN_ON | CLOSE_VALVE
  rlActionId:         number;
  ts:                 string;       // ISO-8601
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
        |> range(start: -${env.dashboardLatestMaxAgeSec}s)
        |> filter(fn: (r) => r._measurement == "gas_reading")
        ${deviceFilter}
        |> pivot(rowKey: ["_time","device_id"], columnKey: ["_field"], valueColumn: "_value")
        |> group()
        |> sort(columns: ["_time"], desc: true)
        |> limit(n: 1)
    `;

    return new Promise((resolve, reject) => {
      const rows: GasReading[] = [];
      this.queryApi.queryRows(flux, {
        next: (row, meta) => {
          const o = meta.toObject(row);
          rows.push({
            deviceId:          String(o["device_id"]            ?? ""),
            gasPpm:            Number(o["gas_ppm"]              ?? 0),
            temperatureC:      Number(o["temperature_c"]        ?? 0),
            humidityPercent:   Number(o["humidity_percent"]     ?? 0),
            lstmRiskScore:     Number(o["lstm_risk_score"]      ?? 0),
            predictedRisk5Min: Number(o["predicted_risk_5min"]  ?? 0),
            riskLabel:         String(o["risk_label"]           ?? "NORMAL"),
            rlAction:          String(o["rl_action"]            ?? "NO_OP"),
            rlActionId:        Number(o["rl_action_id"]         ?? 0),
            ts:                String(o["_time"]                ?? new Date().toISOString()),
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

    const buildFlux = (rangeClause: string) => `
      from(bucket: "${env.influxBucket}")
        |> range(${rangeClause})
        |> filter(fn: (r) => r._measurement == "gas_reading")
        ${deviceFilter}
        |> aggregateWindow(every: ${sampleEvery}s, fn: last, createEmpty: false)
        |> pivot(rowKey: ["_time","device_id"], columnKey: ["_field"], valueColumn: "_value")
        |> group()
        |> sort(columns: ["_time"], desc: false)
    `;

    const queryHistory = (flux: string) => new Promise<GasReading[]>((resolve, reject) => {
      const rows: GasReading[] = [];
      this.queryApi.queryRows(flux, {
        next: (row, meta) => {
          const o = meta.toObject(row);
          rows.push({
            deviceId:          String(o["device_id"]            ?? ""),
            gasPpm:            Number(o["gas_ppm"]              ?? 0),
            temperatureC:      Number(o["temperature_c"]        ?? 0),
            humidityPercent:   Number(o["humidity_percent"]     ?? 0),
            lstmRiskScore:     Number(o["lstm_risk_score"]      ?? 0),
            predictedRisk5Min: Number(o["predicted_risk_5min"]  ?? 0),
            riskLabel:         String(o["risk_label"]           ?? "NORMAL"),
            rlAction:          String(o["rl_action"]            ?? "NO_OP"),
            rlActionId:        Number(o["rl_action_id"]         ?? 0),
            ts:                String(o["_time"]                ?? ""),
          });
        },
        error: reject,
        complete: () => resolve(rows),
      });
    });

    const rows = await queryHistory(buildFlux(`start: -${minutes}m`));
    return rows;
  }
}

// Export singleton
export const influxService = new InfluxService();
