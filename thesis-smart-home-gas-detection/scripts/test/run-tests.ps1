# ─────────────────────────────────────────────────────────────────────────────
# run-tests.ps1  — Install deps (if needed) and run the full Python test suite
#
# Usage:
#   .\run-tests.ps1                     # run all tests
#   .\run-tests.ps1 -pattern lstm       # run only LSTM tests
#   .\run-tests.ps1 -install            # force reinstall deps first
# ─────────────────────────────────────────────────────────────────────────────
param(
    [string]$pattern = "",
    [switch]$install
)

$ROOT = $PSScriptRoot

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "    [FAIL] $msg" -ForegroundColor Red }

# ── Install core test deps (lightweight subset — no pyspark/TF for fast CI) ──
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
    python -m pip install --quiet @testDeps
} else {
    python -m pip install --quiet --upgrade @testDeps 2>&1 | Out-Null
}
Write-OK "Dependencies ready"

# ── Stub-only tests (no TensorFlow/PySpark needed) ───────────────────────────
Write-Step "Running stub unit tests (no model/Spark required)"
$stubArgs = @(
    "-v",
    "--tb=short",
    "--ignore=processing/tests/test_lstm_inference.py",  # skip full LSTM (requires TF + model)
    "processing/tests/"
)
if ($pattern -ne "") { $stubArgs += @("-k", $pattern) }

python -m pytest @stubArgs
$stubExit = $LASTEXITCODE

# ── Full LSTM test (requires TF + best_lstm_uci.keras) ───────────────────────
$modelPath = "$ROOT\processing\ml\lstm\best_lstm_uci.keras"
if (Test-Path $modelPath) {
    Write-Step "Running full LSTM inference tests (model found)"

    # Check tensorflow is importable
    python -c "import tensorflow" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        python -m pytest -v --tb=short processing/tests/test_lstm_inference.py
        $lstmExit = $LASTEXITCODE
    } else {
        Write-Host "    TensorFlow not installed — skipping full LSTM tests" -ForegroundColor Yellow
        Write-Host "    Install with: pip install tensorflow==2.16.1 keras==3.3.3" -ForegroundColor DarkGray
        $lstmExit = 0
    }
} else {
    Write-Host "`n    Model file not found at $modelPath — skipping full LSTM tests" -ForegroundColor Yellow
    $lstmExit = 0
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan
if ($stubExit -eq 0 -and $lstmExit -eq 0) {
    Write-Host " All tests passed ✓" -ForegroundColor Green
} else {
    Write-Host " Some tests FAILED — see output above" -ForegroundColor Red
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkCyan

exit ($stubExit -bor $lstmExit)
