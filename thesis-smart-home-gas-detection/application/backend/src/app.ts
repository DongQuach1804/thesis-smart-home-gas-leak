import express, { Request, Response } from "express";
import cors from "cors";
import helmet from "helmet";
import { apiRouter } from "./routes";
import { requestLogger } from "./middleware/logger";
import { errorHandler, notFound } from "./middleware/error";

export const app = express();

// ── Security headers ──────────────────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }));

// ── CORS ─────────────────────────────────────────────────────────────────────
const corsOrigins: string[] = [
  "http://localhost:8080",
  "http://localhost:3000",
  "http://frontend:8080",
];
const extraOrigin = process.env.BACKEND_BASE_URL;
if (extraOrigin && extraOrigin.startsWith("http")) corsOrigins.push(extraOrigin);

app.use(cors({
  origin: corsOrigins,
  methods: ["GET", "POST", "OPTIONS"],
  allowedHeaders: ["Content-Type", "Authorization"],
  credentials: true,
}));

app.use(express.json());
app.use(requestLogger);

// ── Health endpoint ───────────────────────────────────────────────────────────
app.get("/health", (_req: Request, res: Response) => {
  res.status(200).json({
    status:  "ok",
    service: "gas-detection-backend",
    uptime:  process.uptime(),
    ts:      new Date().toISOString(),
  });
});

// ── API routes ────────────────────────────────────────────────────────────────
app.use("/api", apiRouter);

app.use(notFound);
app.use(errorHandler);
