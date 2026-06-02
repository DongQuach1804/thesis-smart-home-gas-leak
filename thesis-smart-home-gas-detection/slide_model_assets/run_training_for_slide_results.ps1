param(
    [int]$LstmHours = 8,
    [int]$LstmEpochs = 20,
    [int]$PpoSteps = 400000
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "[1/4] Train LSTM forecaster"
python processing/ml/lstm/train_forecaster.py `
    --hours $LstmHours `
    --epochs $LstmEpochs `
    --batch-size 128 `
    --out processing/ml/lstm/gas_forecaster.keras

Write-Host "[2/4] Train PPO v3 controller"
python processing/ml/rl/train_rl.py `
    --steps $PpoSteps `
    --n-envs 4 `
    --episode-seconds 1800 `
    --monitor-dir processing/ml/rl/ppo_monitor `
    --out processing/ml/rl/ppo_gas_agent.zip `
    --vecnormalize-out processing/ml/rl/vecnormalize.pkl

Write-Host "[3/4] Rebuild experiment charts used by thesis/slides"
python thesis-latex/exp_scripts/train_lstm_with_plot.py
python thesis-latex/exp_scripts/train_ppo_with_plot.py
python thesis-latex/exp_scripts/make_confusion_matrix.py
python thesis-latex/exp_scripts/make_benchmark_chart.py
python thesis-latex/exp_scripts/make_scenarios_chart.py
python thesis-latex/exp_scripts/measure_latency.py

Write-Host "[4/4] Generate slide-ready replacement assets"
python slide_model_assets/generate_slide_assets.py

Write-Host "Done. Open slide_model_assets/generated for PNGs and replacement_map.md."
