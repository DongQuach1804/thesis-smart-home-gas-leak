param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("TC1_NORMAL", "TC2_COOKING_CLOSED_ROOM", "TC3_PIPE_JOINT_LEAK", "TC4_RECOVERY", "RANDOM")]
    [string]$Scenario,

    [int]$Seconds = 0
)

$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DeviceId = "esp32-" + $Scenario.ToLowerInvariant().Replace("_", "-")

if ($Seconds -le 0) {
    $Seconds = switch ($Scenario) {
        "TC1_NORMAL" { 120 }
        "TC2_COOKING_CLOSED_ROOM" { 150 }
        "TC3_PIPE_JOINT_LEAK" { 150 }
        "TC4_RECOVERY" { 90 }
        default { 180 }
    }
}

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Push-Location $ROOT
try {
    Write-Step "Starting device-simulator with SIM_SCENARIO=$Scenario"
    $previousScenario = $env:SIM_SCENARIO
    $previousLeakProb = $env:SIM_LEAK_PROB_PER_MIN
    $previousDeviceId = $env:SIM_DEVICE_ID
    $env:SIM_SCENARIO = $Scenario
    $env:SIM_LEAK_PROB_PER_MIN = "0"
    $env:SIM_DEVICE_ID = $DeviceId

    docker compose up -d --no-deps --build --force-recreate device-simulator

    Write-Host "Collecting data for $Seconds seconds." -ForegroundColor Yellow
    Write-Host "  Device ID: $DeviceId" -ForegroundColor Yellow
    Write-Host "  Dashboard: http://127.0.0.1:8080" -ForegroundColor Yellow
    Write-Host "  Latest API: http://localhost:3000/api/dashboard/latest?device_id=$DeviceId" -ForegroundColor Yellow
    Write-Host "  History API: http://localhost:3000/api/dashboard/history?minutes=5&device_id=$DeviceId" -ForegroundColor Yellow
    Start-Sleep -Seconds $Seconds

    Write-Step "Recent simulator logs"
    docker logs --tail 40 device-simulator

    $env:SIM_SCENARIO = $previousScenario
    $env:SIM_LEAK_PROB_PER_MIN = $previousLeakProb
    $env:SIM_DEVICE_ID = $previousDeviceId
}
finally {
    if (Test-Path variable:previousScenario) { $env:SIM_SCENARIO = $previousScenario }
    if (Test-Path variable:previousLeakProb) { $env:SIM_LEAK_PROB_PER_MIN = $previousLeakProb }
    if (Test-Path variable:previousDeviceId) { $env:SIM_DEVICE_ID = $previousDeviceId }
    Pop-Location
}
