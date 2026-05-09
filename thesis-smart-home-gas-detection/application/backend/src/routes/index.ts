import { Router } from "express";
import {
  getLatestReadings,
  getHistoricalReadings,
  getSystemOverview,
  streamAlerts,
  getRecentAlerts,
  getRecentActions,
} from "../controllers/dashboard.controller";

export const apiRouter = Router();

// Dashboard data
apiRouter.get("/dashboard/latest",          getLatestReadings);
apiRouter.get("/dashboard/history",         getHistoricalReadings);
apiRouter.get("/dashboard/overview",        getSystemOverview);
apiRouter.get("/dashboard/alerts",          getRecentAlerts);
apiRouter.get("/dashboard/actions",         getRecentActions);

// Real-time alert stream (SSE)
apiRouter.get("/dashboard/alerts/stream",   streamAlerts);
