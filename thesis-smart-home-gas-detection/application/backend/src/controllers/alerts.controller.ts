import { Request, Response } from "express";
import { z } from "zod";
import { alertStore } from "../services/alert-store.service";

const deviceIdSchema = z.string().trim().max(64).regex(/^[a-zA-Z0-9_\-]+$/).optional();

const listQuery = z.object({
  device_id: deviceIdSchema,
  hours:     z.coerce.number().min(0.0167).max(24 * 7).default(24),
  limit:     z.coerce.number().int().min(1).max(500).default(100),
});

const statsQuery = z.object({
  hours: z.coerce.number().min(0.0167).max(24 * 7).default(24),
});

// ─── GET /api/alerts ──────────────────────────────────────────────────────────

export function listAlerts(req: Request, res: Response): void {
  const q = listQuery.parse(req.query);
  const sinceMs = Date.now() - q.hours * 3_600_000;
  const rows = alertStore.list({
    deviceId: q.device_id,
    sinceMs,
    limit:    q.limit,
  });
  res.status(200).json(rows);
}

// ─── GET /api/alerts/stats ────────────────────────────────────────────────────

export function getAlertStats(req: Request, res: Response): void {
  const { hours } = statsQuery.parse(req.query);
  const sinceMs = Date.now() - hours * 3_600_000;
  res.status(200).json({
    hours,
    ...alertStore.stats(sinceMs),
  });
}

// ─── POST /api/alerts/:id/ack ─────────────────────────────────────────────────

export function ackAlert(req: Request, res: Response): void {
  const updated = alertStore.acknowledge(req.params.id);
  if (!updated) {
    res.status(404).json({ error: "Alert not found", id: req.params.id });
    return;
  }
  res.status(200).json(updated);
}
