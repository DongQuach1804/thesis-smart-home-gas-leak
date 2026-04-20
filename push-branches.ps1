# =============================================================================
# push-branches.ps1
# Pushes the project to GitHub with lean, per-component branches.
#
# Usage:  .\push-branches.ps1
# Run from: d:\IoT\gas-dashboard\gas-dashboard
# =============================================================================

$ErrorActionPreference = "Stop"

$Root       = $PSScriptRoot          # directory where this script lives
$Project    = "thesis-smart-home-gas-detection"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Step { param([string]$msg)
    Write-Host "`n══ $msg " -ForegroundColor Cyan
}
function Write-OK { param([string]$msg)
    Write-Host "  ✓ $msg" -ForegroundColor Green
}
function Write-Warn { param([string]$msg)
    Write-Host "  ⚠ $msg" -ForegroundColor Yellow
}
function Invoke-Git {
    git @args
    if ($LASTEXITCODE -ne 0) { throw "git $args failed (exit $LASTEXITCODE)" }
}

Set-Location $Root

# ── Step 1: Commit everything on main ────────────────────────────────────────
Write-Step "1 / 9 — Preparing main branch"

Invoke-Git checkout -B main

$dirty = git status --porcelain
if ($dirty) {
    Invoke-Git add .
    Invoke-Git commit -m "chore: initial full-project snapshot"
    Write-OK "All files committed to main"
} else {
    Write-OK "Working tree is clean — nothing to commit"
}

# ── Step 2: Push main ─────────────────────────────────────────────────────────
Write-Step "2 / 9 — Pushing main"
Invoke-Git push -u origin main --allow-unrelated-histories --force
Write-OK "main → origin/main"

# ── Helper: orphan branch with only requested paths ───────────────────────────
function Push-LeanBranch {
    param(
        [string]   $Branch,
        [string[]] $Paths,       # paths relative to repo root
        [string]   $Message
    )

    Write-Step "Branch: $Branch"

    # Always return to main first
    Invoke-Git checkout main --quiet

    # Create a brand-new orphan branch (no history)
    Invoke-Git checkout --orphan $Branch --quiet

    # Wipe the index so we start empty
    git rm -rf . --quiet 2>$null | Out-Null

    # Restore only the wanted paths from main
    $anyRestored = $false
    foreach ($p in $Paths) {
        git checkout main -- $p 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "  added: $p"
            $anyRestored = $true
        } else {
            Write-Warn "  not found on main: $p (skipped)"
        }
    }

    # Always bring root shared files along for context
    foreach ($f in @(".gitignore", ".gitattributes")) {
        git checkout main -- $f 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $anyRestored = $true }
    }

    if (-not $anyRestored) {
        Write-Warn "Nothing restored — skipping branch $Branch"
        Invoke-Git checkout main --quiet
        git branch -D $Branch 2>$null | Out-Null
        return
    }

    # Commit
    $staged = git diff --cached --name-only
    if ($staged) {
        Invoke-Git commit -m $Message --quiet
        Write-OK "Committed"
    }

    # Force-push (safe since orphan has no shared history)
    Invoke-Git push -u origin $Branch --force --quiet
    Write-OK "Pushed → origin/$Branch"

    # Back to main
    Invoke-Git checkout main --quiet
}

# ── Step 3–9: Lean feature branches ──────────────────────────────────────────

Push-LeanBranch `
    -Branch  "feature/device" `
    -Paths   @("$Project/device") `
    -Message "feat(device): ESP32 firmware and sensor simulator"

Push-LeanBranch `
    -Branch  "feature/communication" `
    -Paths   @("$Project/communication") `
    -Message "feat(communication): MQTT bridge and message routing"

Push-LeanBranch `
    -Branch  "feature/processing" `
    -Paths   @("$Project/processing") `
    -Message "feat(processing): Spark streaming, LSTM, RL inference pipeline"

Push-LeanBranch `
    -Branch  "feature/application" `
    -Paths   @("$Project/application") `
    -Message "feat(application): Node.js backend and EJS frontend dashboard"

Push-LeanBranch `
    -Branch  "feature/infrastructure" `
    -Paths   @("$Project/infrastructure") `
    -Message "feat(infrastructure): Mosquitto, InfluxDB, Grafana, PostgreSQL config"

Push-LeanBranch `
    -Branch  "feature/deploy" `
    -Paths   @("$Project/deploy", "$Project/scripts") `
    -Message "feat(deploy): Dockerfiles, Compose files, and DevOps scripts"

Push-LeanBranch `
    -Branch  "feature/docs" `
    -Paths   @("$Project/docs", "$Project/README.md", "$Project/.env.example") `
    -Message "docs: project documentation and environment variable template"

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  All branches pushed to GitHub!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host @"

  Branch layout:
    main                   full project snapshot (all files)
    feature/device         ESP32 firmware + sensor simulator
    feature/communication  MQTT bridge
    feature/processing     Spark + LSTM + RL pipeline
    feature/application    Node.js backend + EJS frontend
    feature/infrastructure Mosquitto / InfluxDB / Grafana / PG config
    feature/deploy         Dockerfiles + Compose + scripts
    feature/docs           Docs + README + .env.example

  View: https://github.com/DongQuach1804/thesis-smart-home-gas-leak
"@ -ForegroundColor White
