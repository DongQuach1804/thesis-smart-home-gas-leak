import express, { Request, Response } from "express";
import cors from "cors";
import helmet from "helmet";
import swaggerUi from "swagger-ui-express";
import { apiRouter } from "./routes";
import { openApiSpec } from "./docs/openapi";

export const app = express();

// ── Security headers ──────────────────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));

// ── CORS ─────────────────────────────────────────────────────────────────────
// Build the allow-list: always include localhost and Docker-internal frontend,
// plus any extra origin from the environment variable (e.g. remote server IP).
const corsOrigins: string[] = [
  "http://localhost:8080",
  "http://localhost:3000",
  "http://127.0.0.1:8080",
  "http://127.0.0.1:3000",
  "http://frontend:8080",
];

const extraOrigin = process.env.BACKEND_BASE_URL;
if (extraOrigin && extraOrigin.startsWith("http")) {
  corsOrigins.push(extraOrigin);
}

app.use(cors({
  origin: corsOrigins,
  methods: ["GET", "POST", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
  credentials: true,
}));

// ── Body parsing ──────────────────────────────────────────────────────────────
app.use(express.json());

// ── Health endpoint ───────────────────────────────────────────────────────────
app.get("/health", (_req: Request, res: Response) => {
  res.status(200).json({
    status:  "ok",
    service: "gas-detection-backend",
    ts:      new Date().toISOString(),
  });
});

// ── API docs ───────────────────────────────────────────────────────────────
app.get("/api/docs.json", (_req: Request, res: Response) => {
  res.status(200).json(openApiSpec);
});
app.use("/api/docs", swaggerUi.serve, swaggerUi.setup(openApiSpec, { explorer: true }));

// ── API routes ────────────────────────────────────────────────────────────────
app.use("/api", apiRouter);
