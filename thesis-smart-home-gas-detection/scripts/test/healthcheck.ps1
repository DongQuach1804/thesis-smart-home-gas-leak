# ─────────────────────────────────────────────────────────────────────────────
# healthcheck.ps1  — Quick end-to-end pipeline health verification
# ─────────────────────────────────────────────────────────────────────────────

function Test-Endpoint([string]$label, [string]$url) {
    try {
        $resp = Invoke-RestMethod -Uri $url -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  [OK]  $label — $url" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [!!]  $label — $url  ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

function Test-KafkaTopic([string]$topic) {
    $result = docker exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic $topic 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]  Kafka topic exists: $topic" -ForegroundColor Green
    } else {
        Write-Host "  [!!]  Kafka topic missing: $topic" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host " Gas Leak Pipeline — Health Check" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
Write-Host ""

Write-Host "[ HTTP Endpoints ]" -ForegroundColor DarkGray
Test-Endpoint "Backend health"     "http://localhost:3000/health"
Test-Endpoint "API latest"         "http://localhost:3000/api/dashboard/latest"
Test-Endpoint "API history"        "http://localhost:3000/api/dashboard/history?minutes=5"
Test-Endpoint "API overview"       "http://localhost:3000/api/dashboard/overview"
Test-Endpoint "Frontend"           "http://localhost:8080"
Test-Endpoint "InfluxDB health"    "http://localhost:8086/health"
Test-Endpoint "Grafana"            "http://localhost:3001/api/health"

Write-Host ""
Write-Host "[ Kafka Topics ]" -ForegroundColor DarkGray
Test-KafkaTopic "gas.raw.sensor"
Test-KafkaTopic "gas.alert.events"

Write-Host ""
Write-Host "[ InfluxDB Data ]" -ForegroundColor DarkGray
try {
    $body = @{ query = 'from(bucket:"gas_sensor_data") |> range(start:-5m) |> limit(n:1)' } | ConvertTo-Json
    $resp = Invoke-RestMethod -Method Post -Uri "http://localhost:8086/api/v2/query?org=thesis-org" `
        -Headers @{ Authorization = "Token thesis-super-token"; "Content-Type" = "application/json" } `
        -Body $body -TimeoutSec 5
    Write-Host "  [OK]  InfluxDB has recent gas_sensor_data" -ForegroundColor Green
} catch {
    Write-Host "  [!!]  InfluxDB query failed or no recent data" -ForegroundColor Yellow
}

Write-Host ""
