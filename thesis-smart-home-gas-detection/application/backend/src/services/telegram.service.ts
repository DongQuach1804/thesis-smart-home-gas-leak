import { env } from "../config/env";
import type { AlertEvent } from "./kafka.consumer";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

class TelegramService {
  private readonly enabled: boolean;
  private readonly token: string;
  private readonly chatId: string;
  private readonly minRiskScore: number;
  private readonly cooldownMs: number;
  private readonly allowedLabels: Set<string> | null;
  private readonly lastSentByKey = new Map<string, number>();
  private warnedDisabled = false;
  private warnedNotConfigured = false;

  constructor() {
    this.enabled = TRUE_VALUES.has(env.telegramEnabled.toLowerCase());
    this.token = env.telegramBotToken;
    this.chatId = env.telegramChatId;
    this.minRiskScore = Number.isFinite(env.telegramMinRiskScore) ? env.telegramMinRiskScore : 0.7;
    this.cooldownMs = Math.max(0, env.telegramCooldownSec) * 1000;

    const labels = env.telegramRiskLabels
      .split(",")
      .map((label) => label.trim().toUpperCase())
      .filter(Boolean);
    this.allowedLabels = labels.length ? new Set(labels) : null;

    if (!this.enabled) {
      console.info("[telegram] disabled: set TELEGRAM_ENABLED=true to send alerts");
    } else if (!this.token || !this.chatId) {
      console.warn("[telegram] enabled but TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing");
    } else {
      console.info(
        `[telegram] enabled: minRiskScore=${this.minRiskScore}, cooldownSec=${this.cooldownMs / 1000}`,
      );
    }
  }

  private isReady(): boolean {
    if (!this.enabled) {
      if (!this.warnedDisabled) {
        console.warn("[telegram] skipped: TELEGRAM_ENABLED is not true");
        this.warnedDisabled = true;
      }
      return false;
    }
    if (!this.token || !this.chatId) {
      if (!this.warnedNotConfigured) {
        console.warn("[telegram] skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing");
        this.warnedNotConfigured = true;
      }
      return false;
    }
    return true;
  }

  private passesFilters(alert: AlertEvent): boolean {
    if (!Number.isFinite(alert.riskScore)) {
      console.warn("[telegram] skipped: alert riskScore is not finite");
      return false;
    }
    if (alert.riskScore < this.minRiskScore) {
      console.info(
        `[telegram] skipped: risk ${alert.riskScore.toFixed(4)} < threshold ${this.minRiskScore}`,
      );
      return false;
    }

    if (this.allowedLabels) {
      const label = (alert.riskLabel || "").toUpperCase();
      if (!this.allowedLabels.has(label)) {
        console.info(`[telegram] skipped: risk label ${label || "(empty)"} is not enabled`);
        return false;
      }
    }

    return true;
  }

  private buildMessage(alert: AlertEvent): string {
    const ts = this.formatTime(alert.eventTs);
    const sourceLabel = alert.alertSource === "REALTIME_GAS"
      ? "Real/simulation gas threshold"
      : alert.alertSource === "LSTM_FORECAST"
        ? "LSTM forecast threshold"
        : alert.alertSource;
    return [
      `GAS ALERT - ${sourceLabel}`,
      `alert_time: ${ts}`,
      `device: ${alert.deviceId}`,
      `gas_ppm: ${alert.gasPpm.toFixed(1)}`,
      `risk_label: ${alert.riskLabel}`,
      `risk_score: ${alert.riskScore.toFixed(4)}`,
      `lstm_prediction_5min: ${alert.predictedRisk5Min.toFixed(4)}`,
      `rl_action: ${alert.rlAction} (${alert.rlActionId})`,
      `event_ts: ${ts}`,
    ].join("\n");
  }

  private formatTime(ts: number): string {
    return new Intl.DateTimeFormat("vi-VN", {
      timeZone: env.displayTimeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(new Date(ts));
  }

  async notifyAlert(alert: AlertEvent): Promise<void> {
    if (!this.isReady()) return;
    if (!this.passesFilters(alert)) return;

    const now = Date.now();
    const cooldownKey = `${alert.deviceId}:${alert.alertSource}:${alert.riskLabel}`;
    const lastSent = this.lastSentByKey.get(cooldownKey) ?? 0;
    if (now - lastSent < this.cooldownMs) {
      console.info(`[telegram] skipped: cooldown active for ${cooldownKey}`);
      return;
    }
    this.lastSentByKey.set(cooldownKey, now);

    const url = `https://api.telegram.org/bot${this.token}/sendMessage`;
    const body = {
      chat_id: this.chatId,
      text: this.buildMessage(alert),
    };

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        const tail = detail ? ` ${detail}` : "";
        console.warn(`[telegram] sendMessage failed: ${res.status} ${res.statusText}${tail}`);
        return;
      }

      console.info(`[telegram] alert sent for device ${alert.deviceId}`);
    } catch (err) {
      console.warn("[telegram] sendMessage error:", (err as Error).message);
    }
  }
}

export const telegramService = new TelegramService();
