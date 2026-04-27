const express = require("express");
const path    = require("path");

const app  = express();
const port = Number(process.env.FRONTEND_PORT || 8080);

// BACKEND_BASE_URL must be reachable FROM THE BROWSER (host machine), not from
// inside the Docker network. docker-compose.yml sets this to http://localhost:3000.
const backendBaseUrl = process.env.BACKEND_BASE_URL || "http://localhost:3000";

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.static(path.join(__dirname, "public")));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "frontend", backendBaseUrl });
});

app.get("/", (_req, res) => {
  res.render("dashboard", {
    backendBaseUrl,
    appVersion: process.env.npm_package_version || "1.0.0",
  });
});

app.listen(port, () => {
  console.log(`Frontend listening on port ${port}`);
  console.log(`Backend API URL for browser: ${backendBaseUrl}`);
});
