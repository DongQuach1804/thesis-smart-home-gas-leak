import dotenv from "dotenv";
import { app } from "./app";
import { alertConsumer } from "./services/kafka.consumer";

dotenv.config();

const port = Number(process.env.API_PORT ?? 3000);

// Start Kafka alert consumer (non-blocking — logs warning if Kafka unavailable)
alertConsumer.start().catch((err) =>
  console.warn("[server] Kafka consumer failed to start:", err)
);

app.listen(port, () => {
  console.log(`Backend listening on ${port}`);
});
