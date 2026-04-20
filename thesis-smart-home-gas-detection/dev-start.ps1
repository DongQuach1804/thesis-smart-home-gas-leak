# ─────────────────────────────────────────────────────────────────────────────
# dev-start.ps1  — One-command Docker dev startup
#
# Usage:
#   .\dev-start.ps1             # Build + start all services
#   .\dev-start.ps1 -infra      # Start only infra containers (no app services)
#   .\dev-start.ps1 -stop       # Stop and remove all containers
#   .\dev-start.ps1 -logs       # Tail logs for all services
# ─────────────────────────────────────────────────────────────────────────────
param(
    [switch]$infra,
    [switch]$stop,
    [switch]$logs
)

$ROOT        = $PSScriptRoot
$COMPOSE     = "docker compose"
$COMPOSE_DEV = "$COMPOSE -f docker-compose.yml -f docker-compose.dev.yml"

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    [!]  $msg" -ForegroundColor Yellow }

Set-Location $ROOT

# ── Stop ──────────────────────────────────────────────────────────────────────
if ($stop) {
    Write-Step "Stopping all containers"
    Invoke-Expression "$COMPOSE down"
    Write-OK "All containers stopped"
    exit 0
}

# ── Logs ──────────────────────────────────────────────────────────────────────
if ($logs) {
    Invoke-Expression "$COMPOSE_DEV logs -f"
    exit 0
}

# ── .env check ────────────────────────────────────────────────────────────────
Write-Step "Checking .env"
if (-not (Test-Path "$ROOT\.env")) {
    Copy-Item "$ROOT\.env.example" "$ROOT\.env"
    Write-Warn ".env created from .env.example — review it before running in production"
}
Write-OK ".env exists"

# ── Infrastructure only ───────────────────────────────────────────────────────
if ($infra) {
    Write-Step "Starting infrastructure only (mosquitto, kafka, influxdb, postgres, grafana)"
    Invoke-Expression "$COMPOSE up -d mosquitto kafka influxdb postgres grafana"
    Write-OK "Infrastructure started"
    Write-Host ""
    Write-Host "  InfluxDB  http://localhost:8086" -ForegroundColor White
    Write-Host "  Grafana   http://localhost:3001  (admin / admin123456)" -ForegroundColor White
    exit 0
}

# ── Full Docker build + start ─────────────────────────────────────────────────
Write-Step "Building and starting all services (this may take a few minutes on first run)"
Write-Warn "Kafka connector JARs are downloaded during processing-engine build..."

Invoke-Expression "$COMPOSE_DEV up -d --build"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] docker compose failed — check output above" -ForegroundColor Red
    exit 1
}

Write-OK "All containers started"

# ── Wait for key services ─────────────────────────────────────────────────────
Write-Step "Waiting for services to become healthy..."

function Wait-Healthy([string]$name, [int]$maxSec = 120) {
    $t = 0
    while ($t -lt $maxSec) {
        $status = docker inspect --format="{{.State.Health.Status}}" $name 2>$null
        if ($status -eq "healthy") { Write-OK "$name is healthy"; return $true }
        Start-Sleep 5; $t += 5
        Write-Host "    ... waiting for $name ($t/${maxSec}s)" -ForegroundColor DarkGray
    }
    Write-Warn "$name did not become healthy after ${maxSec}s"
    return $false
}

Wait-Healthy "kafka"   120
Wait-Healthy "influxdb" 60

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host " Smart Home Gas Leak Detection — All Services Running" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  Dashboard    http://localhost:8080" -ForegroundColor White
Write-Host "  Backend API  http://localhost:3000/health" -ForegroundColor White
Write-Host "  InfluxDB     http://localhost:8086" -ForegroundColor White
Write-Host "  Grafana      http://localhost:3001  (admin / admin123456)" -ForegroundColor White
Write-Host ""
Write-Host "  Kafka (Docker-internal) : kafka:9092" -ForegroundColor DarkGray
Write-Host "  Kafka (Host access)     : localhost:9093" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  View logs  : .\dev-start.ps1 -logs" -ForegroundColor DarkGray
Write-Host "  Stop all   : .\dev-start.ps1 -stop" -ForegroundColor DarkGray
Write-Host ""
