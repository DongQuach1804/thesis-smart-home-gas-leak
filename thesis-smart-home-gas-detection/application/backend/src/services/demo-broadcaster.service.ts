/**
 * Demo broadcaster — when DEMO_FALLBACK is on and Kafka isn't producing,
 * emit a heartbeat of synthetic readings + occasional alerts so the UI
 * has something to display end-to-end.
 *
 * Wired into the same EventEmitter shape as the Kafka consumer (`alert` event)
 * and exposes a `reading` event for the readings SSE stream.
 */
import EventEmitter from "events";
import { env } from "../config/env";
import { syntheticReading, demoDevices } from "./mock-data.service";
import { alertStore } from "./alert-store.service";
import type { AlertEvent } from "./kafka.consumer";

class DemoBroadcaster extends EventEmitter {
  private timer: NodeJS.Timeout | null = null;

  start(): void {
    if (this.timer || !env.demoFallback) return;

    this.timer = setInterval(() => {
      const device  = demoDevices[Math.floor(Math.random() * demoDevices.length)];
      const reading = syntheticReading(device);

      this.emit("reading", reading);

      if (reading.riskLabel !== "NORMAL") {
        const alert: AlertEvent = {
          deviceId:  reading.deviceId,
          gasPpm:    reading.gasPpm,
          riskScore: reading.lstmRiskScore,
          riskLabel: reading.riskLabel,
          eventTs:   Date.now(),
        };
        alertStore.push(alert);
        this.emit("alert", alert);
      }
    }, 3_000);

    console.log("[DemoBroadcaster] Started (DEMO_FALLBACK=true)");
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }
}

export const demoBroadcaster = new DemoBroadcaster();
