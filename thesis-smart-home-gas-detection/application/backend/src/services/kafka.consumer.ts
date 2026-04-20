/**
 * Kafka consumer for gas.alert.events topic.
 *
 * Fix for apache/kafka:3.9.x + KafkaJS compatibility:
 *  - KafkaJS defaults cause "Response without match" + JoinGroup timeout loops
 *    against newer Kafka brokers that use Fetch API v11+.
 *  - Fixes: increase requestTimeout, tune session/heartbeat, cap maxWaitTimeInMs,
 *    and use a longer retry back-off so the broker isn't hammered.
 */
import { Kafka, Consumer, EachMessagePayload, logLevel } from "kafkajs";
import EventEmitter from "events";
import { env } from "../config/env";

export interface AlertEvent {
  deviceId:  string;
  gasPpm:    number;
  riskScore: number;
  riskLabel: string;
  eventTs:   number;
}

class KafkaAlertConsumer extends EventEmitter {
  private consumer: Consumer | null = null;
  private running = false;

  async start(): Promise<void> {
    if (this.running) return;

    const kafka = new Kafka({
      clientId:          "gas-backend",
      brokers:           [env.kafkaBroker],
      // ── Timeouts tuned for apache/kafka KRaft mode ──────────────────────
      connectionTimeout: 15_000,   // ms to wait for TCP connection
      requestTimeout:    60_000,   // ms before a request is considered timed out
      // ── Suppress noisy "Response without match" WARN logs ───────────────
      logLevel:          logLevel.ERROR,
      // ── Retry with gentle back-off so we don't hammer the broker ────────
      retry: {
        initialRetryTime: 3_000,
        retries:          20,
        maxRetryTime:     60_000,
        factor:           1.5,
      },
    });

    this.consumer = kafka.consumer({
      groupId:           "gas-backend-alerts",
      // ── Session / heartbeat tuned for slow-starting Docker environment ──
      sessionTimeout:    45_000,   // broker kicks member after this ms of silence
      heartbeatInterval: 5_000,    // send heartbeat every 5 s (must be < sessionTimeout/3)
      // ── Fetch tuning: cap wait so connections don't idle into timeout ───
      maxWaitTimeInMs:   5_000,    // max ms to wait for data before returning empty
      retry:             { retries: 10 },
    });

    try {
      await this.consumer.connect();
      await this.consumer.subscribe({
        topic:         env.kafkaAlertTopic,
        fromBeginning: false,
      });

      await this.consumer.run({
        eachMessage: async ({ message }: EachMessagePayload) => {
          try {
            const raw = message.value?.toString();
            if (!raw) return;
            const payload = JSON.parse(raw);
            const alert: AlertEvent = {
              deviceId:  payload.device_id  ?? "unknown",
              gasPpm:    Number(payload.gas_ppm   ?? 0),
              riskScore: Number(payload.risk_score ?? 0),
              riskLabel: payload.risk_label  ?? "ALERT",
              eventTs:   Number(payload.event_ts  ?? Date.now()),
            };
            this.emit("alert", alert);
          } catch {
            // malformed message — ignore
          }
        },
      });

      this.running = true;
      console.log(`[KafkaConsumer] Subscribed to ${env.kafkaAlertTopic}`);
    } catch (err) {
      console.warn(
        "[KafkaConsumer] Could not connect — alerts disabled:",
        (err as Error).message,
      );
    }
  }

  async stop(): Promise<void> {
    await this.consumer?.disconnect();
    this.running = false;
  }
}

export const alertConsumer = new KafkaAlertConsumer();
