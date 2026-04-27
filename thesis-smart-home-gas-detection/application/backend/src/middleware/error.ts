import { NextFunction, Request, Response } from "express";
import { ZodError } from "zod";

/** Wrap async route handlers so thrown errors reach the error middleware. */
export function asyncHandler<T extends (req: Request, res: Response, next: NextFunction) => Promise<unknown> | unknown>(fn: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

export function notFound(_req: Request, res: Response): void {
  res.status(404).json({ error: "Not found" });
}

export function errorHandler(
  err: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction,
): void {
  if (err instanceof ZodError) {
    res.status(400).json({
      error:  "Invalid request",
      issues: err.issues.map(i => ({ path: i.path.join("."), message: i.message })),
    });
    return;
  }
  const message = err instanceof Error ? err.message : String(err);
  console.error("[errorHandler]", err);
  res.status(500).json({ error: "Internal server error", detail: message });
}
