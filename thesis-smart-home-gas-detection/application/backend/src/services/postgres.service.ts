/**
 * Thin Postgres helper for persisting alerts and RL action events.
 *
 * Uses `pg` Pool. If Postgres is unreachable at startup we log and degrade
 * gracefully so the rest of the API stays alive.
 */
import { Pool } from "pg";
import { env } from "../config/env";

export interface AlertRow {
  deviceId:           string;
  gasPpm:             number;
  predictedRisk5Min:  number;
  riskLabel:          string;
  eventTs:            number;
}

export interface ActionRow {
  deviceId:   string;
  action:     string;
  actionId:   number;
  triggerP5:  number;
  gasPpm:     number;
  eventTs:    number;
}

class PostgresService {
  private pool: Pool;
  private healthy = false;

  constructor() {
    this.pool = new Pool({
      host:     env.postgresHost,
      port:     env.postgresPort,
      database: env.postgresDb,
      user:     env.postgresUser,
      password: env.postgresPassword,
      max:      10,
      idleTimeoutMillis: 30_000,
    });
    this.pool.on("error", err => {
      console.warn("[postgres] pool error:", err.message);
      this.healthy = false;
    });
    this.ping();
  }

  async ping(): Promise<void> {
    try {
      await this.pool.query("SELECT 1");
      this.healthy = true;
      console.log("[postgres] connected");
    } catch (err) {
      console.warn("[postgres] not reachable:", (err as Error).message);
      this.healthy = false;
    }
  }

  isHealthy(): boolean {
    return this.healthy;
  }

  async insertAlert(a: AlertRow): Promise<void> {
    if (!this.healthy) return;
    try {
      await this.pool.query(
        `INSERT INTO alert_events
           (device_id, gas_ppm, predicted_risk_5min, risk_label, event_ts)
         VALUES ($1, $2, $3, $4, $5)`,
        [a.deviceId, a.gasPpm, a.predictedRisk5Min, a.riskLabel, a.eventTs],
      );
    } catch (err) {
      console.warn("[postgres] insertAlert failed:", (err as Error).message);
    }
  }

  async insertAction(a: ActionRow): Promise<void> {
    if (!this.healthy) return;
    try {
      await this.pool.query(
        `INSERT INTO action_events
           (device_id, action, action_id, trigger_p5, gas_ppm, event_ts)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [a.deviceId, a.action, a.actionId, a.triggerP5, a.gasPpm, a.eventTs],
      );
    } catch (err) {
      console.warn("[postgres] insertAction failed:", (err as Error).message);
    }
  }

  async recentAlerts(limit = 50): Promise<unknown[]> {
    if (!this.healthy) return [];
    const r = await this.pool.query(
      `SELECT device_id AS "deviceId",
              gas_ppm AS "gasPpm",
              predicted_risk_5min AS "predictedRisk5Min",
              risk_label AS "riskLabel",
              event_ts AS "eventTs",
              created_at AS "createdAt"
         FROM alert_events
        ORDER BY event_ts DESC
        LIMIT $1`,
      [limit],
    );
    return r.rows;
  }

  async recentActions(limit = 50): Promise<unknown[]> {
    if (!this.healthy) return [];
    const r = await this.pool.query(
      `SELECT device_id AS "deviceId",
              action,
              action_id AS "actionId",
              trigger_p5 AS "triggerP5",
              gas_ppm AS "gasPpm",
              event_ts AS "eventTs",
              created_at AS "createdAt"
         FROM action_events
        ORDER BY event_ts DESC
        LIMIT $1`,
      [limit],
    );
    return r.rows;
  }
}

export const postgresService = new PostgresService();
