import { Router } from "express";
import {
  getLatestReadings,
  getHistoricalReadings,
  getStats,
  getSystemOverview,
  streamAlerts,
  streamReadings,
} from "../controllers/dashboard.controller";
import { listDevices, getDevice } from "../controllers/devices.controller";
import { listAlerts, getAlertStats, ackAlert } from "../controllers/alerts.controller";
import { asyncHandler } from "../middleware/error";

export const apiRouter = Router();

// Dashboard data
apiRouter.get("/dashboard/latest",          asyncHandler(getLatestReadings));
apiRouter.get("/dashboard/history",         asyncHandler(getHistoricalReadings));
apiRouter.get("/dashboard/stats",           asyncHandler(getStats));
apiRouter.get("/dashboard/overview",        asyncHandler(getSystemOverview));

// Real-time streams (SSE)
apiRouter.get("/dashboard/alerts/stream",   streamAlerts);
apiRouter.get("/dashboard/readings/stream", streamReadings);

// Devices
apiRouter.get("/devices",                   asyncHandler(listDevices));
apiRouter.get("/devices/:id",               asyncHandler(getDevice));

// Alerts history
apiRouter.get("/alerts",                    asyncHandler(listAlerts));
apiRouter.get("/alerts/stats",              asyncHandler(getAlertStats));
apiRouter.post("/alerts/:id/ack",           asyncHandler(ackAlert));
