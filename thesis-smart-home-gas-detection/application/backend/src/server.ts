import "dotenv/config";
import { app } from "./app";
import { alertConsumer } from "./services/kafka.consumer";
import { demoBroadcaster } from "./services/demo-broadcaster.service";
import { env } from "./config/env";

const port = env.apiPort;

// Start Kafka alert consumer (non-blocking — logs warning if Kafka unavailable)
alertConsumer.start().catch((err) =>
  console.warn("[server] Kafka consumer failed to start:", err),
);

// Start demo broadcaster (no-op when DEMO_FALLBACK is false)
demoBroadcaster.start();

const server = app.listen(port, () => {
  console.log(`Backend listening on ${port} (${env.nodeEnv})`);
  if (env.demoFallback) console.log("[server] DEMO_FALLBACK enabled — synthetic data will be served if real sources are empty");
});

function shutdown(signal: string) {
  console.log(`[server] received ${signal}, shutting down…`);
  demoBroadcaster.stop();
  alertConsumer.stop().catch(() => undefined);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5_000).unref();
}

process.on("SIGINT",  () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
