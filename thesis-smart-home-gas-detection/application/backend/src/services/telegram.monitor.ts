import { env } from "../config/env";
import { influxService, type GasReading } from "./influx.service";
import { telegramService } from "./telegram.service";
import type { AlertEvent } from "./kafka.consumer";

class TelegramRealtimeMonitor {
  private timer: NodeJS.Timeout | null = null;
  private running = false;
  private lastState = "INIT";

  start(): void {
    if (this.timer) return;
    const intervalMs = Math.max(1, env.telegramMonitorIntervalSec) * 1000;

    this.timer = setInterval(() => {
      void this.tick();
    }, intervalMs);

    void this.tick();
    console.info(`[telegram-monitor] started: intervalSec=${intervalMs / 1000}`);
  }

  stop(): void {
    if (!this.timer) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  private deriveLabel(reading: GasReading): string {
    const label = (reading.riskLabel || "").toUpperCase();
    if (["ALERT", "WARNING", "CRITICAL"].includes(label)) return label;
    if (reading.gasPpm >= env.gasAlertPpm) return "ALERT";
    if (reading.gasPpm >= env.gasWarningPpm) return "WARNING";
    return "NORMAL";
  }

  private riskScore(reading: GasReading): number {
    const modelScore = Number(reading.predictedRisk5Min ?? reading.lstmRiskScore ?? 0);
    const gasScore = env.gasAlertPpm > 0 ? reading.gasPpm / env.gasAlertPpm : 0;
    return Math.min(Math.max(modelScore, gasScore, 0), 1);
  }

  private toAlert(reading: GasReading, label: string): AlertEvent {
    const eventTs = Date.parse(reading.ts);
    const action = label === "ALERT"
      ? "CLOSE_VALVE"
      : label === "WARNING"
        ? "FAN_ON"
        : reading.rlAction;
    const actionId = action === "CLOSE_VALVE" ? 3 : action === "FAN_ON" ? 2 : reading.rlActionId;
    const score = this.riskScore(reading);

    return {
      deviceId:          reading.deviceId,
      gasPpm:            reading.gasPpm,
      predictedRisk5Min: score,
      riskLabel:         label,
      eventTs:           Number.isFinite(eventTs) ? eventTs : Date.now(),
      alertSource:       "REALTIME_GAS",
      alertTime:         reading.ts,
      rlAction:          action,
      rlActionId:        actionId,
      lstmRiskScore:     reading.lstmRiskScore,
      lstmRiskLabel:     reading.riskLabel,
      riskScore:         score,
    };
  }

  private async tick(): Promise<void> {
    if (this.running) return;
    this.running = true;

    try {
      const reading = await influxService.getLatestReading();
      if (!reading) {
        this.logState("NO_FRESH_DATA");
        return;
      }

      const label = this.deriveLabel(reading);
      if (label === "NORMAL") {
        this.logState(`NORMAL:${reading.deviceId}`);
        return;
      }

      this.logState(`${label}:${reading.deviceId}`);
      await telegramService.notifyAlert(this.toAlert(reading, label));
    } catch (err) {
      console.warn("[telegram-monitor] tick failed:", (err as Error).message);
    } finally {
      this.running = false;
    }
  }

  private logState(state: string): void {
    if (state === this.lastState) return;
    this.lastState = state;
    console.info(`[telegram-monitor] state=${state}`);
  }
}

export const telegramRealtimeMonitor = new TelegramRealtimeMonitor();
