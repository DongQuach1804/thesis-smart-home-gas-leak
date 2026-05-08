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
      requestTimeout:    90_000,   // increased to handle KRaft leader election
      // ── Suppress noisy "Response without match" WARN logs ───────────────
      logLevel:          logLevel.ERROR,
      // ── Limit retries so consumer stops after giving up (not infinite loop) ──
      retry: {
        initialRetryTime: 5_000,
        retries:          5,        // give up after 5 attempts (~2 min total)
        maxRetryTime:     30_000,
        factor:           2.0,
      },
    });

    this.consumer = kafka.consumer({
      groupId:           "gas-backend-alerts",
      // ── Session / heartbeat tuned for slow-starting Docker environment ──
      sessionTimeout:    45_000,   // broker kicks member after this ms of silence
      heartbeatInterval: 5_000,    // send heartbeat every 5 s (must be < sessionTimeout/3)
      // ── Fetch tuning: cap wait so connections don't idle into timeout ───
      maxWaitTimeInMs:   5_000,    // max ms to wait for data before returning empty
      retry:             { retries: 3 },
    });

    try {
      // Give Kafka broker extra time to be fully ready in Docker
      await new Promise(resolve => setTimeout(resolve, 5_000));

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
        "[KafkaConsumer] Could not connect after retries — real-time alerts disabled. REST APIs unaffected.",
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
