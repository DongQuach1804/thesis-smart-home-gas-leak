import { NextFunction, Request, Response } from "express";

/** Lightweight access logger — skips SSE streams to avoid log spam. */
export function requestLogger(req: Request, res: Response, next: NextFunction): void {
  if (req.path.endsWith("/stream")) return next();
  const start = Date.now();
  res.on("finish", () => {
    const ms = Date.now() - start;
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl} → ${res.statusCode} (${ms}ms)`);
  });
  next();
}
