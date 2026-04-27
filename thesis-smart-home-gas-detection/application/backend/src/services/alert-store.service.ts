/**
 * In-memory ring buffer of recent alert events.
 *
 * The Kafka consumer pushes every alert into this store; HTTP controllers
 * read from it for the alert-history endpoint. Keeping it in memory keeps
 * the backend self-contained — no DB schema migrations required just to
 * see "what fired in the last hour".
 */
import { randomUUID } from "crypto";
import type { AlertEvent } from "./kafka.consumer";

export interface StoredAlert extends AlertEvent {
  id:          string;
  acknowledged: boolean;
  receivedAt:  number;
}

const MAX_ALERTS = 500;

class AlertStore {
  private buffer: StoredAlert[] = [];

  push(alert: AlertEvent): StoredAlert {
    const stored: StoredAlert = {
      ...alert,
      id:           randomUUID(),
      acknowledged: false,
      receivedAt:   Date.now(),
    };
    this.buffer.unshift(stored);
    if (this.buffer.length > MAX_ALERTS) this.buffer.length = MAX_ALERTS;
    return stored;
  }

  list(opts: { deviceId?: string; sinceMs?: number; limit?: number } = {}): StoredAlert[] {
    const { deviceId, sinceMs, limit = 100 } = opts;
    let rows = this.buffer;
    if (deviceId)         rows = rows.filter(a => a.deviceId === deviceId);
    if (typeof sinceMs === "number") rows = rows.filter(a => a.receivedAt >= sinceMs);
    return rows.slice(0, limit);
  }

  acknowledge(id: string): StoredAlert | null {
    const a = this.buffer.find(x => x.id === id);
    if (!a) return null;
    a.acknowledged = true;
    return a;
  }

  stats(sinceMs: number): { total: number; warning: number; alert: number; devicesAffected: number } {
    const recent = this.buffer.filter(a => a.receivedAt >= sinceMs);
    const devices = new Set(recent.map(a => a.deviceId));
    return {
      total:           recent.length,
      warning:         recent.filter(a => a.riskLabel === "WARNING").length,
      alert:           recent.filter(a => a.riskLabel === "ALERT").length,
      devicesAffected: devices.size,
    };
  }
}

export const alertStore = new AlertStore();
