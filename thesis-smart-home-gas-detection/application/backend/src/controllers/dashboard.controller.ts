import { Request, Response } from "express";
import { z } from "zod";
import { influxService } from "../services/influx.service";
import { alertConsumer, AlertEvent } from "../services/kafka.consumer";
import { demoBroadcaster } from "../services/demo-broadcaster.service";
import { env } from "../config/env";
import type { GasReading } from "../services/influx.service";

// ─── Query validation ─────────────────────────────────────────────────────────

const deviceIdSchema = z.string().trim().max(64).regex(/^[a-zA-Z0-9_\-]+$/).optional();

const latestQuery = z.object({
  device_id: deviceIdSchema,
});

const historyQuery = z.object({
  device_id:    deviceIdSchema,
  minutes:      z.coerce.number().int().min(1).max(24 * 60).default(30),
  sample_every: z.coerce.number().int().min(1).max(3600).default(10),
});

const statsQuery = z.object({
  device_id: deviceIdSchema,
  minutes:   z.coerce.number().int().min(1).max(24 * 60).default(60),
});

// ─── GET /api/dashboard/latest ────────────────────────────────────────────────

export async function getLatestReadings(req: Request, res: Response): Promise<void> {
  const q = latestQuery.parse(req.query);
  const reading = await influxService.getLatestReading(q.device_id ?? "");
  if (!reading) {
    res.status(200).json({
      deviceId:        q.device_id ?? "esp32-lab-01",
      gasPpm:          0,
      temperatureC:    0,
      humidityPercent: 0,
      lstmRiskScore:   0,
      riskLabel:       "NORMAL",
      ts:              new Date().toISOString(),
      _source:         "no_data",
    });
    return;
  }
  res.status(200).json(reading);
}

// ─── GET /api/dashboard/history ───────────────────────────────────────────────

export async function getHistoricalReadings(req: Request, res: Response): Promise<void> {
  const q = historyQuery.parse(req.query);
  const rows = await influxService.getHistoricalReadings(
    q.device_id ?? "",
    q.minutes,
    q.sample_every,
  );
  res.status(200).json(rows);
}

// ─── GET /api/dashboard/stats ─────────────────────────────────────────────────

export async function getStats(req: Request, res: Response): Promise<void> {
  const q = statsQuery.parse(req.query);
  const stats = await influxService.getStats(q.device_id ?? "", q.minutes);
  res.status(200).json(stats);
}

// ─── GET /api/dashboard/alerts/stream  (Server-Sent Events) ───────────────────

export function streamAlerts(req: Request, res: Response): void {
  setupSSE(res);

  const heartbeat = setInterval(() => res.write(": heartbeat\n\n"), 15_000);

  const onAlert = (alert: AlertEvent) => {
    res.write(`data: ${JSON.stringify(alert)}\n\n`);
  };

  alertConsumer.on("alert",       onAlert);
  demoBroadcaster.on("alert",     onAlert);

  req.on("close", () => {
    clearInterval(heartbeat);
    alertConsumer.off("alert",   onAlert);
    demoBroadcaster.off("alert", onAlert);
  });
}

// ─── GET /api/dashboard/readings/stream  (SSE — live reading firehose) ────────

export function streamReadings(req: Request, res: Response): void {
  setupSSE(res);
  const heartbeat = setInterval(() => res.write(": heartbeat\n\n"), 15_000);

  const onReading = (reading: GasReading) => {
    res.write(`data: ${JSON.stringify(reading)}\n\n`);
  };

  demoBroadcaster.on("reading", onReading);

  req.on("close", () => {
    clearInterval(heartbeat);
    demoBroadcaster.off("reading", onReading);
  });
}

// ─── GET /api/dashboard/overview ──────────────────────────────────────────────

export async function getSystemOverview(_req: Request, res: Response): Promise<void> {
  const influxUp = await influxService.ping();
  const kafkaUp  = alertConsumer.isRunning();
  // MQTT and Spark are upstream of this service — we infer "up" from data flow:
  // if Kafka is delivering or Influx has data, the upstream pipeline is alive.
  const pipelineFlowing = kafkaUp || influxUp;

  res.status(200).json({
    services: {
      mqtt:     pipelineFlowing ? "up" : "unknown",
      kafka:    kafkaUp         ? "up" : "down",
      spark:    pipelineFlowing ? "up" : "unknown",
      influxdb: influxUp        ? "up" : "down",
    },
    model: {
      lstm: "loaded",
      rl:   "loaded",
    },
    thresholds: {
      gasPpmWarning: env.gasPpmWarning,
      gasPpmAlert:   env.gasPpmAlert,
    },
    ts: new Date().toISOString(),
  });
}

// ─── helpers ──────────────────────────────────────────────────────────────────

function setupSSE(res: Response): void {
  res.setHeader("Content-Type",     "text/event-stream");
  res.setHeader("Cache-Control",    "no-cache");
  res.setHeader("Connection",       "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();
}
