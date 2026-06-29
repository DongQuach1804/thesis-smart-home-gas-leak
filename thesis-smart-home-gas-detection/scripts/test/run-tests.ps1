# run-tests.ps1 - Run the Python processing test suite locally or in Docker
#
# Usage:
#   .\run-tests.ps1                 # run all supported tests
#   .\run-tests.ps1 -pattern lstm   # run tests matching pattern
#   .\run-tests.ps1 -install        # force reinstall deps first when using local Python

param(
    [string]$pattern = "",
    [switch]$install
)

$ROOT = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$originalLocation = Get-Location

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg) { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "    [FAIL] $msg" -ForegroundColor Red }

function Test-LocalPython {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { return $false }

    python --version 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Test-ContainerRunning([string]$name) {
    $containerId = docker ps --filter "name=$name" --filter "status=running" -q 2>$null
    return -not [string]::IsNullOrWhiteSpace($containerId)
}

function Invoke-ExternalCommand([string[]]$commandArgs) {
    & $commandArgs[0] $commandArgs[1..($commandArgs.Length - 1)] 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

function Invoke-LocalTests {
    Write-Step "Checking / installing test dependencies"

    $testDeps = @(
        "numpy==1.26.4",
        "kafka-python==2.0.2",
        "influxdb-client==1.43.0",
        "pytest==8.2.2",
        "paho-mqtt==2.1.0",
        "python-dotenv==1.0.1"
    )

    if ($install) {
        Write-Host "    Force reinstalling..." -ForegroundColor DarkGray
        python -m pip install @testDeps
    } else {
        python -m pip install --upgrade @testDeps
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Dependency installation failed"
        return $LASTEXITCODE
    }

    Write-OK "Dependencies ready"

    Write-Step "Running stub unit tests locally (no model/Spark required)"
    $stubArgs = @(
        "-v",
        "--tb=short",
        "--ignore=processing/tests/test_lstm_inference.py",
        "processing/tests/"
    )

    if ($pattern -ne "") {
        $stubArgs += @("-k", $pattern)
    }

    python -m pytest @stubArgs
    $stubExit = $LASTEXITCODE

    $modelPath = Join-Path $ROOT "processing\ml\lstm\gas_forecaster.keras"
    if (Test-Path $modelPath) {
        Write-Step "Running full LSTM inference tests (model found)"

        python -c "import tensorflow" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            python -m pytest -v --tb=short processing/tests/test_lstm_inference.py
            $lstmExit = $LASTEXITCODE
        } else {
            Write-Host "    TensorFlow not installed locally - trying Docker..." -ForegroundColor Yellow
            $lstmExit = Invoke-DockerLstmTests
        }
    } else {
        Write-Host "`n    Model file not found at $modelPath - skipping full LSTM tests" -ForegroundColor Yellow
        $lstmExit = 0
    }

    return ($stubExit -bor $lstmExit)
}

function Invoke-DockerStubTests {
    if (-not (Test-ContainerRunning "processing-engine")) {
        Write-Fail "Docker container 'processing-engine' is not running"
        Write-Host "    Start with: docker compose up -d" -ForegroundColor DarkGray
        return 1
    }

    Write-Step "Running stub unit tests inside processing-engine container"
    $dockerArgs = @(
        "docker",
        "exec",
        "-w", "/app",
        "processing-engine",
        "python", "-m", "pytest",
        "-v",
        "--tb=short",
        "--ignore=/app/tests/test_lstm_inference.py",
        "/app/tests/"
    )

    if ($pattern -ne "") {
        $dockerArgs += @("-k", $pattern)
    }

    return (Invoke-ExternalCommand $dockerArgs)
}

function Invoke-DockerLstmTests {
    if (-not (Test-ContainerRunning "processing-engine")) {
        Write-Host "    Docker container 'processing-engine' is not running; skipping full LSTM tests." -ForegroundColor DarkGray
        return 0
    }

    Write-Host "    [Docker] Running LSTM tests inside processing-engine container..." -ForegroundColor Cyan
    $dockerArgs = @(
        "docker",
        "exec",
        "-w", "/app",
        "processing-engine",
        "python", "-m", "pytest",
        "/app/tests/test_lstm_inference.py",
        "-v",
        "--tb=short"
    )

    return (Invoke-ExternalCommand $dockerArgs)
}

try {
    Push-Location $ROOT

    if (Test-LocalPython) {
        $exitCode = Invoke-LocalTests
    } else {
        Write-Host "    Local Python was not found or is only the Microsoft Store alias." -ForegroundColor Yellow
        Write-Host "    Falling back to Docker container tests." -ForegroundColor Yellow
        $stubExit = Invoke-DockerStubTests
        $lstmExit = Invoke-DockerLstmTests
        $exitCode = ($stubExit -bor $lstmExit)
    }

    Write-Host ""
    Write-Host "=================================================" -ForegroundColor DarkCyan
    if ($exitCode -eq 0) {
        Write-Host " All tests passed" -ForegroundColor Green
    } else {
        Write-Host " Some tests FAILED - see output above" -ForegroundColor Red
    }
    Write-Host "=================================================" -ForegroundColor DarkCyan

    exit $exitCode
} finally {
    Set-Location $originalLocation
}
