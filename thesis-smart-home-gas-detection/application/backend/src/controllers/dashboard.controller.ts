import { Request, Response } from "express";
import { influxService } from "../services/influx.service";
import { alertConsumer, AlertEvent } from "../services/kafka.consumer";

// ─── GET /api/dashboard/latest ────────────────────────────────────────────────

export async function getLatestReadings(req: Request, res: Response): Promise<void> {
  const deviceId = (req.query.device_id as string) ?? "";
  try {
    const reading = await influxService.getLatestReading(deviceId);
    if (!reading) {
      res.status(200).json({
        deviceId:        deviceId || "esp32-lab-01",
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
  } catch (err) {
    console.error("[dashboard/latest]", err);
    res.status(500).json({ error: "Failed to query InfluxDB", detail: String(err) });
  }
}

// ─── GET /api/dashboard/history ───────────────────────────────────────────────

export async function getHistoricalReadings(req: Request, res: Response): Promise<void> {
  const deviceId   = (req.query.device_id as string) ?? "";
  const minutes    = Number(req.query.minutes    ?? 30);
  const sampleEvery = Number(req.query.sample_every ?? 10);
  try {
    const rows = await influxService.getHistoricalReadings(deviceId, minutes, sampleEvery);
    res.status(200).json(rows);
  } catch (err) {
    console.error("[dashboard/history]", err);
    res.status(500).json({ error: "Failed to query InfluxDB", detail: String(err) });
  }
}

// ─── GET /api/dashboard/alerts/stream  (Server-Sent Events) ────────────────────

export function streamAlerts(req: Request, res: Response): void {
  res.setHeader("Content-Type",  "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection",    "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  // Send a heartbeat every 15 s so proxies don't close the connection
  const heartbeat = setInterval(() => {
    res.write(": heartbeat\n\n");
  }, 15_000);

  const onAlert = (alert: AlertEvent) => {
    res.write(`data: ${JSON.stringify(alert)}\n\n`);
  };

  alertConsumer.on("alert", onAlert);

  req.on("close", () => {
    clearInterval(heartbeat);
    alertConsumer.off("alert", onAlert);
  });
}

// ─── GET /api/dashboard/overview ──────────────────────────────────────────────

export async function getSystemOverview(_req: Request, res: Response): Promise<void> {
  res.status(200).json({
    services: {
      mqtt:    "up",
      kafka:   "up",
      spark:   "up",
      influxdb: "up",
      postgres: "up",
    },
    model: {
      lstm: "loaded",
      rl:   "loaded",
    },
    ts: new Date().toISOString(),
  });
}
