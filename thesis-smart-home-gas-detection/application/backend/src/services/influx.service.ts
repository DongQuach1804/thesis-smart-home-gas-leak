/**
 * InfluxDB service — Flux queries for gas sensor readings and LSTM predictions.
 *
 * Uses @influxdata/influxdb-client (the official v2 client).
 * All Flux queries return strongly-typed domain objects.
 *
 * Each query is wrapped in a try/catch and, when DEMO_FALLBACK is enabled,
 * falls back to synthesised data so the dashboard still works without a
 * running Influx instance.
 */
import { InfluxDB, QueryApi } from "@influxdata/influxdb-client";
import { env } from "../config/env";
import { syntheticReading, syntheticHistory, demoDevices } from "./mock-data.service";

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

export interface ReadingStats {
  count:        number;
  avgPpm:       number;
  maxPpm:       number;
  minPpm:       number;
  avgRiskScore: number;
  windowMins:   number;
}

/** Drop anything outside [A-Za-z0-9_-] so the value can be safely embedded in Flux. */
function sanitizeDeviceId(id: string): string {
  return (id ?? "").replace(/[^a-zA-Z0-9_\-]/g, "").slice(0, 64);
}

// ─── Service ──────────────────────────────────────────────────────────────────

class InfluxService {
  private readonly queryApi: QueryApi;

  constructor() {
    const client = new InfluxDB({ url: env.influxUrl, token: env.influxToken });
    this.queryApi = client.getQueryApi(env.influxOrg);
  }

  /** Latest sensor reading for a device (or the most recent device if omitted). */
  async getLatestReading(deviceId = ""): Promise<GasReading | null> {
    const safeId = sanitizeDeviceId(deviceId);
    const deviceFilter = safeId
      ? `|> filter(fn: (r) => r.device_id == "${safeId}")`
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

    try {
      const reading = await this.runQuery(flux);
      if (reading.length > 0) return reading[0];
    } catch (err) {
      if (!env.demoFallback) throw err;
    }
    if (env.demoFallback) {
      return syntheticReading(deviceId || demoDevices[0]);
    }
    return null;
  }

  /** Historical readings for charting. */
  async getHistoricalReadings(
    deviceId = "",
    minutes = 30,
    sampleEvery = 10,
  ): Promise<GasReading[]> {
    const safeId = sanitizeDeviceId(deviceId);
    const deviceFilter = safeId
      ? `|> filter(fn: (r) => r.device_id == "${safeId}")`
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

    try {
      const rows = await this.runQuery(flux);
      if (rows.length > 0) return rows;
    } catch (err) {
      if (!env.demoFallback) throw err;
    }
    if (env.demoFallback) {
      return syntheticHistory(deviceId || demoDevices[0], minutes, sampleEvery);
    }
    return [];
  }

  /** Aggregate stats over a window. Falls back to summarising synthetic history. */
  async getStats(deviceId = "", minutes = 60): Promise<ReadingStats> {
    const rows = await this.getHistoricalReadings(deviceId, minutes, 30);
    if (rows.length === 0) {
      return { count: 0, avgPpm: 0, maxPpm: 0, minPpm: 0, avgRiskScore: 0, windowMins: minutes };
    }
    const sum  = rows.reduce((a, r) => a + r.gasPpm, 0);
    const sumR = rows.reduce((a, r) => a + r.lstmRiskScore, 0);
    return {
      count:        rows.length,
      avgPpm:       Number((sum  / rows.length).toFixed(2)),
      maxPpm:       Number(Math.max(...rows.map(r => r.gasPpm)).toFixed(2)),
      minPpm:       Number(Math.min(...rows.map(r => r.gasPpm)).toFixed(2)),
      avgRiskScore: Number((sumR / rows.length).toFixed(4)),
      windowMins:   minutes,
    };
  }

  /** Lightweight liveness probe for the overview endpoint. */
  async ping(): Promise<boolean> {
    const flux = `from(bucket: "${env.influxBucket}") |> range(start: -1m) |> limit(n: 1)`;
    try {
      await new Promise<void>((resolve, reject) => {
        this.queryApi.queryRows(flux, {
          next: () => undefined,
          error: reject,
          complete: () => resolve(),
        });
      });
      return true;
    } catch {
      return false;
    }
  }

  /** List distinct device IDs that have reported recently. */
  async listDevices(minutes = 60): Promise<string[]> {
    const flux = `
      from(bucket: "${env.influxBucket}")
        |> range(start: -${minutes}m)
        |> filter(fn: (r) => r._measurement == "gas_reading")
        |> keep(columns: ["device_id"])
        |> distinct(column: "device_id")
    `;
    try {
      const ids = await new Promise<string[]>((resolve, reject) => {
        const acc: string[] = [];
        this.queryApi.queryRows(flux, {
          next: (row, meta) => {
            const o = meta.toObject(row);
            const id = String(o["device_id"] ?? o["_value"] ?? "");
            if (id) acc.push(id);
          },
          error: reject,
          complete: () => resolve(acc),
        });
      });
      const unique = Array.from(new Set(ids));
      if (unique.length > 0) return unique;
    } catch {
      // fall through to demo
    }
    return env.demoFallback ? [...demoDevices] : [];
  }

  // ─── Internal helpers ───────────────────────────────────────────────────────

  private runQuery(flux: string): Promise<GasReading[]> {
    return new Promise((resolve, reject) => {
      const rows: GasReading[] = [];
      this.queryApi.queryRows(flux, {
        next: (row, meta) => {
          const o = meta.toObject(row);
          rows.push({
            deviceId:        String(o["device_id"]        ?? ""),
            gasPpm:          Number(o["gas_ppm"]           ?? 0),
            temperatureC:    Number(o["temperature_c"]     ?? 0),
            humidityPercent: Number(o["humidity_percent"]  ?? 0),
            lstmRiskScore:   Number(o["lstm_risk_score"]   ?? 0),
            riskLabel:       String(o["risk_label"]        ?? "NORMAL"),
            ts:              String(o["_time"]             ?? new Date().toISOString()),
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
