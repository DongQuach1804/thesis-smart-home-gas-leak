import { Request, Response } from "express";
import { influxService } from "../services/influx.service";

interface DeviceSummary {
  deviceId:    string;
  status:      "online" | "offline";
  lastSeen:    string | null;
  lastPpm:     number | null;
  lastRisk:    number | null;
  lastLabel:   string | null;
  location?:   string;
}

/** Static metadata. In a fuller deployment this comes from Postgres. */
const DEVICE_LOCATIONS: Record<string, string> = {
  "esp32-lab-01":      "Lab — Bench A",
  "esp32-kitchen-02":  "Kitchen — Hood",
  "esp32-garage-03":   "Garage — Wall",
};

// ─── GET /api/devices ─────────────────────────────────────────────────────────

export async function listDevices(_req: Request, res: Response): Promise<void> {
  const ids = await influxService.listDevices(60);
  const summaries: DeviceSummary[] = await Promise.all(
    ids.map(async (id) => {
      const r = await influxService.getLatestReading(id);
      const lastSeenMs = r ? new Date(r.ts).getTime() : 0;
      const online = r ? Date.now() - lastSeenMs < 60_000 : false;
      return {
        deviceId:  id,
        status:    online ? "online" : "offline",
        lastSeen:  r ? r.ts : null,
        lastPpm:   r ? r.gasPpm : null,
        lastRisk:  r ? r.lstmRiskScore : null,
        lastLabel: r ? r.riskLabel : null,
        location:  DEVICE_LOCATIONS[id],
      };
    }),
  );
  res.status(200).json(summaries);
}

// ─── GET /api/devices/:id ─────────────────────────────────────────────────────

export async function getDevice(req: Request, res: Response): Promise<void> {
  const id = req.params.id;
  const r  = await influxService.getLatestReading(id);
  if (!r) {
    res.status(404).json({ error: "Device not found", deviceId: id });
    return;
  }
  res.status(200).json({
    deviceId:  id,
    location:  DEVICE_LOCATIONS[id],
    latest:    r,
  });
}
