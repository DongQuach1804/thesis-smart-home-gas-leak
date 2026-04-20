const express = require("express");
const path    = require("path");

const app  = express();
const port = Number(process.env.FRONTEND_PORT || 8080);

// BACKEND_BASE_URL is injected at Docker runtime.
// It must be reachable FROM THE BROWSER (the host machine), not from inside
// the Docker network.  docker-compose.yml sets this to http://localhost:3000.
// Fallback to localhost for local dev without Docker.
const backendBaseUrl = process.env.BACKEND_BASE_URL || "http://localhost:3000";

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.static(path.join(__dirname, "public")));

// Health endpoint for Docker healthcheck
app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "frontend", backendBaseUrl });
});

app.get("/", (_req, res) => {
  res.render("dashboard", { backendBaseUrl });
});

app.listen(port, () => {
  console.log(`Frontend listening on port ${port}`);
  console.log(`Backend API URL for browser: ${backendBaseUrl}`);
});
