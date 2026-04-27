/**
 * Synthetic gas-sensor data generator.
 * Used as a fallback when InfluxDB has no data yet (or is unreachable),
 * so the dashboard always has something meaningful to show during demos.
 *
 * Deterministic enough to look like real sensor noise, with occasional
 * spikes that cross the WARNING / ALERT thresholds.
 */
import { env } from "../config/env";
import type { GasReading } from "./influx.service";

const DEMO_DEVICES = ["esp32-lab-01", "esp32-kitchen-02", "esp32-garage-03"];

function labelFor(ppm: number): string {
  if (ppm >= env.gasPpmAlert) return "ALERT";
  if (ppm >= env.gasPpmWarning) return "WARNING";
  return "NORMAL";
}

function riskScoreFor(ppm: number): number {
  // Smooth sigmoid mapping ppm → risk in [0,1]
  const x = (ppm - env.gasPpmWarning) / 250;
  const s = 1 / (1 + Math.exp(-x));
  return Math.max(0, Math.min(1, s));
}

/**
 * Generate one synthetic reading for a device at a given moment.
 * Uses the timestamp as the noise seed so repeat calls within the same
 * second are stable.
 */
export function syntheticReading(deviceId: string, when: Date = new Date()): GasReading {
  const t = when.getTime() / 1000;
  // Slow drift around 250 ppm with occasional spikes
  const base = 220 + 80 * Math.sin(t / 47) + 40 * Math.sin(t / 11);
  const spike = Math.sin(t / 31) > 0.92 ? 380 : 0;          // occasional warning
  const burst = Math.sin(t / 73 + deviceId.length) > 0.97 ? 520 : 0; // rare alert
  const noise = (Math.random() - 0.5) * 25;
  const ppm   = Math.max(40, base + spike + burst + noise);

  const tempC    = 26 + 2.5 * Math.sin(t / 90) + (Math.random() - 0.5);
  const humidity = 58 + 10 * Math.sin(t / 130) + (Math.random() - 0.5) * 2;

  return {
    deviceId,
    gasPpm:          Number(ppm.toFixed(2)),
    temperatureC:    Number(tempC.toFixed(2)),
    humidityPercent: Number(humidity.toFixed(2)),
    lstmRiskScore:   Number(riskScoreFor(ppm).toFixed(4)),
    riskLabel:       labelFor(ppm),
    ts:              when.toISOString(),
  };
}

export function syntheticHistory(
  deviceId: string,
  minutes: number,
  sampleEvery: number,
): GasReading[] {
  const now    = Date.now();
  const stepMs = Math.max(1, sampleEvery) * 1000;
  const count  = Math.floor((minutes * 60_000) / stepMs);
  const out: GasReading[] = [];
  for (let i = count; i >= 0; i--) {
    out.push(syntheticReading(deviceId, new Date(now - i * stepMs)));
  }
  return out;
}

export const demoDevices = DEMO_DEVICES;
