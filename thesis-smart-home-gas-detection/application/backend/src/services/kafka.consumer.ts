/**
 * Kafka consumers for the gas-leak pipeline.
 *
 *   gas.alert.events   — predictive alerts from the forecasting LSTM
 *   gas.action.events  — actions chosen by the RL controller
 *
 * Both topics are mirrored to Postgres so the dashboard / thesis report
 * can query persistent history.
 */
import { Kafka, Consumer, EachMessagePayload, logLevel } from "kafkajs";
import EventEmitter from "events";
import { env } from "../config/env";
import { postgresService } from "./postgres.service";
import { telegramService } from "./telegram.service";

const TRUE_VALUES = new Set(["1", "true", "yes", "on"]);

export interface AlertEvent {
  deviceId:           string;
  gasPpm:             number;
  predictedRisk5Min:  number;     // P(critical in 5 min) from forecaster
  riskLabel:          string;
  eventTs:            number;
  alertSource:        string;
  alertTime:          string;
  rlAction:           string;
  rlActionId:         number;
  lstmRiskScore:      number;
  lstmRiskLabel:      string;
  // Legacy alias preserved so existing SSE clients still parse "riskScore"
  riskScore:          number;
}

export interface ActionEvent {
  deviceId:   string;
  action:     string;
  actionId:   number;
  triggerP5:  number;
  gasPpm:     number;
  eventTs:    number;
}

class KafkaPipelineConsumer extends EventEmitter {
  private alertConsumer: Consumer | null = null;
  private actionConsumer: Consumer | null = null;
  private running = false;

  private normalizeEventTs(raw: unknown): number {
    const parsed = Number(raw ?? Date.now());
    if (!Number.isFinite(parsed) || parsed <= 0) return Date.now();
    return parsed < 1_000_000_000_000 ? parsed * 1000 : parsed;
  }

  private isStaleEvent(eventTs: number): boolean {
    const maxAgeMs = Math.max(0, env.alertMaxAgeSec) * 1000;
    if (maxAgeMs === 0) return false;
    return Date.now() - eventTs > maxAgeMs;
  }

  async start(): Promise<void> {
    if (this.running) return;

    const kafka = new Kafka({
      clientId:          "gas-backend",
      brokers:           [env.kafkaBroker],
      connectionTimeout: 15_000,
      requestTimeout:    300_000,
      logLevel:          logLevel.ERROR,
      retry: {
        initialRetryTime: 5_000,
        retries:          5,        // give up after 5 attempts (~2 min total)
        maxRetryTime:     60_000,
        factor:           2.0,
      },
    });

    const baseOpts = {
      sessionTimeout:    60_000,
      rebalanceTimeout:  300_000,
      heartbeatInterval: 5_000,
      maxWaitTimeInMs:   5_000,
      retry:             { retries: 10 },
    };

    // ── Alerts ────────────────────────────────────────────────────────────
    this.alertConsumer = kafka.consumer({ groupId: env.kafkaAlertGroupId, ...baseOpts });
    try {
      await new Promise(resolve => setTimeout(resolve, 5_000));
      await this.alertConsumer.connect();
      await this.alertConsumer.subscribe({ topic: env.kafkaAlertTopic, fromBeginning: false });
      await this.alertConsumer.run({
        eachMessage: async ({ message }: EachMessagePayload) => {
          try {
            const raw = message.value?.toString();
            if (!raw) return;
            const p = JSON.parse(raw);
            const p5 = Number(p.predicted_risk_5min ?? p.risk_score ?? 0);
            const eventTs = this.normalizeEventTs(p.event_ts);
            if (this.isStaleEvent(eventTs)) {
              console.warn(
                "[KafkaConsumer] skipped stale alert: device=%s source=%s ageSec=%s",
                p.device_id ?? "unknown",
                p.alert_source ?? "unknown",
                Math.round((Date.now() - eventTs) / 1000),
              );
              return;
            }
            const alert: AlertEvent = {
              deviceId:          p.device_id ?? "unknown",
              gasPpm:            Number(p.gas_ppm ?? 0),
              predictedRisk5Min: p5,
              riskLabel:         p.risk_label ?? "ALERT",
              eventTs,
              alertSource:       p.alert_source ?? "LSTM_FORECAST",
              alertTime:         p.alert_time ?? new Date(eventTs).toISOString(),
              rlAction:          p.rl_action ?? "NO_OP",
              rlActionId:        Number(p.rl_action_id ?? 0),
              lstmRiskScore:     Number(p.lstm_risk_score ?? 0),
              lstmRiskLabel:     p.lstm_risk_label ?? "NORMAL",
              riskScore:         Number(p.risk_score ?? p5),
            };
            this.emit("alert", alert);
            if (TRUE_VALUES.has(env.telegramNotifyFromKafka.toLowerCase())) {
              void telegramService.notifyAlert(alert);
            }
            await postgresService.insertAlert({
              deviceId:          alert.deviceId,
              gasPpm:            alert.gasPpm,
              predictedRisk5Min: alert.predictedRisk5Min,
              riskLabel:         alert.riskLabel,
              eventTs:           alert.eventTs,
            });
          } catch {
            /* ignore malformed */
          }
        },
      });
      console.log(`[KafkaConsumer] subscribed: ${env.kafkaAlertTopic}`);
    } catch (err) {
      console.warn(
        "[KafkaConsumer] alert consumer disabled — real-time alerts off, REST APIs unaffected:",
        (err as Error).message,
      );
    }

    // ── Actions ───────────────────────────────────────────────────────────
    this.actionConsumer = kafka.consumer({ groupId: env.kafkaActionGroupId, ...baseOpts });
    try {
      await this.actionConsumer.connect();
      await this.actionConsumer.subscribe({ topic: env.kafkaActionTopic, fromBeginning: false });
      await this.actionConsumer.run({
        eachMessage: async ({ message }: EachMessagePayload) => {
          try {
            const raw = message.value?.toString();
            if (!raw) return;
            const p = JSON.parse(raw);
            const eventTs = this.normalizeEventTs(p.event_ts);
            const event: ActionEvent = {
              deviceId:  p.device_id ?? "unknown",
              action:    p.action ?? "NO_OP",
              actionId:  Number(p.action_id ?? 0),
              triggerP5: Number(p.trigger_p5 ?? 0),
              gasPpm:    Number(p.gas_ppm ?? 0),
              eventTs,
            };
            this.emit("action", event);
            await postgresService.insertAction(event);
          } catch {
            /* ignore */
          }
        },
      });
      console.log(`[KafkaConsumer] subscribed: ${env.kafkaActionTopic}`);
    } catch (err) {
      console.warn("[KafkaConsumer] action consumer disabled:", (err as Error).message);
    }

    this.running = true;
  }

  async stop(): Promise<void> {
    await this.alertConsumer?.disconnect();
    await this.actionConsumer?.disconnect();
    this.running = false;
  }
}

export const alertConsumer = new KafkaPipelineConsumer();
